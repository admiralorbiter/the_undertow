"""
Clustering service.
Clusters articles using HDBSCAN with k-means fallback.
"""
import logging
import numpy as np
import sqlite3
from typing import Tuple, List, Dict
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import hdbscan
from backend.db import get_db
from backend.config import Config
from backend.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class ClusteringService:
    """Service for clustering articles using HDBSCAN or k-means."""
    
    def __init__(self):
        """Initialize clustering service."""
        self.embedding_service = EmbeddingService()
        self.min_cluster_size = Config.CLUSTER_MIN_SIZE
        self.min_samples = Config.CLUSTER_MIN_SAMPLES
        
    def _load_embeddings(self) -> Tuple[np.ndarray, List[int]]:
        """
        Load all embeddings from database.
        
        Returns:
            tuple: (embeddings_array, article_ids_list)
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT e.article_id, e.vec
                FROM embeddings e
                ORDER BY e.article_id
            """)
            rows = cursor.fetchall()
            
            if len(rows) == 0:
                return np.array([]), []
            
            embeddings = []
            article_ids = []
            
            for row in rows:
                vector = self.embedding_service._blob_to_vector(row['vec'])
                embeddings.append(vector)
                article_ids.append(row['article_id'])
            
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Normalize for cosine similarity
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            embeddings_array = embeddings_array / norms
            
            return embeddings_array, article_ids
            
        finally:
            conn.close()
    
    def _cluster_hdbscan(self, embeddings: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Cluster embeddings using HDBSCAN.
        
        Args:
            embeddings: Normalized embedding vectors
            
        Returns:
            tuple: (labels, n_clusters)
            labels: cluster labels (-1 for noise)
            n_clusters: number of clusters found
        """
        logger.info(f"Running HDBSCAN with min_cluster_size={self.min_cluster_size}, "
                   f"min_samples={self.min_samples}")
        
        # HDBSCAN doesn't support 'cosine' metric directly
        # Use 'euclidean' on normalized vectors (equivalent to cosine distance)
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric='euclidean'  # Euclidean on normalized vectors = cosine distance
        )
        
        labels = clusterer.fit_predict(embeddings)
        
        # Count clusters (excluding noise label -1)
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        
        logger.info(f"HDBSCAN found {n_clusters} clusters and {np.sum(labels == -1)} noise points")
        
        return labels, n_clusters
    
    def _cluster_kmeans(self, embeddings: np.ndarray, k_range: Tuple[int, int] = (2, 20)) -> Tuple[np.ndarray, int]:
        """
        Cluster embeddings using k-means with silhouette score optimization.
        
        Args:
            embeddings: Normalized embedding vectors
            k_range: Range of k values to try (min, max)
            
        Returns:
            tuple: (labels, k_optimal)
            labels: cluster labels
            k_optimal: optimal number of clusters
        """
        logger.info(f"Running k-means optimization over k_range={k_range}")
        
        n_samples = len(embeddings)
        k_min, k_max = k_range
        
        # Adjust k_max if we have fewer samples
        k_max = min(k_max, max(2, n_samples // self.min_cluster_size))
        k_min = max(2, min(k_min, k_max))
        
        if k_min > k_max:
            logger.warning(f"Adjusted k_range: using k={k_min}")
            kmeans = KMeans(n_clusters=k_min, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            return labels, k_min
        
        best_score = -1
        best_k = k_min
        best_labels = None
        best_kmeans = None
        
        # Try different k values
        for k in range(k_min, k_max + 1):
            if k > n_samples:
                break
            
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            
            # Calculate silhouette score
            if len(set(labels)) > 1:  # Need at least 2 clusters for silhouette
                try:
                    score = silhouette_score(embeddings, labels, sample_size=min(1000, n_samples))
                except Exception as e:
                    logger.warning(f"Error calculating silhouette for k={k}: {e}")
                    score = -1
                
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_labels = labels
                    best_kmeans = kmeans
        
        if best_labels is None:
            # Fallback: just use k_min
            logger.warning("Could not optimize k-means, using k_min")
            kmeans = KMeans(n_clusters=k_min, random_state=42, n_init=10)
            best_labels = kmeans.fit_predict(embeddings)
            best_k = k_min
        
        logger.info(f"k-means optimal k={best_k} (silhouette={best_score:.3f})")
        
        return best_labels, best_k
    
    def _update_article_clusters(self, article_ids: List[int], labels: np.ndarray):
        """
        Update articles.cluster_id in database.
        
        Args:
            article_ids: List of article IDs (same order as labels)
            labels: Cluster labels from clustering
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Update cluster_id for each article
            # Use NULL for noise points (label == -1)
            updates = []
            for article_id, label in zip(article_ids, labels):
                cluster_id = int(label) if label >= 0 else None
                updates.append((cluster_id, article_id))
            
            cursor.executemany("""
                UPDATE articles SET cluster_id = ? WHERE id = ?
            """, updates)
            
            conn.commit()
            
            # Count articles per cluster
            cluster_counts = {}
            for label in labels:
                if label >= 0:
                    cluster_counts[int(label)] = cluster_counts.get(int(label), 0) + 1
            
            logger.info(f"Updated cluster_id for {len(updates)} articles")
            logger.info(f"Cluster distribution: {len(cluster_counts)} clusters")
            
        except Exception as e:
            logger.error(f"Error updating article clusters: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _update_clusters_table(self, labels: np.ndarray):
        """
        Create/update clusters table with cluster metadata.
        
        Args:
            labels: Cluster labels from clustering
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Clear existing clusters
            cursor.execute("DELETE FROM clusters")
            
            # Count articles per cluster
            cluster_counts = {}
            for label in labels:
                if label >= 0:
                    cluster_id = int(label)
                    cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
            
            # Insert cluster records (labels will be updated in step 7)
            for cluster_id, size in sorted(cluster_counts.items()):
                cursor.execute("""
                    INSERT INTO clusters (id, label, size, score)
                    VALUES (?, ?, ?, ?)
                """, (cluster_id, None, size, 0.0))
            
            conn.commit()
            
            logger.info(f"Updated clusters table: {len(cluster_counts)} clusters")
            
        except Exception as e:
            logger.error(f"Error updating clusters table: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def cluster_articles(self, force_recompute=False) -> Dict:
        """
        Cluster articles using HDBSCAN with k-means fallback.
        
        Args:
            force_recompute: If True, recompute even if clusters exist
            
        Returns:
            dict with stats: {'clusters_created': int, 'articles_clustered': int, 'noise': int, 'method': str}
        """
        logger.info("Clustering articles...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Check if clustering already done
            if not force_recompute:
                cursor.execute("SELECT COUNT(*) FROM articles WHERE cluster_id IS NOT NULL")
                clustered_count = cursor.fetchone()[0]
                
                if clustered_count > 0:
                    cursor.execute("SELECT COUNT(*) FROM clusters")
                    clusters_count = cursor.fetchone()[0]
                    logger.info(f"Clustering already exists: {clustered_count} articles, {clusters_count} clusters")
                    return {
                        'clusters_created': clusters_count,
                        'articles_clustered': clustered_count,
                        'noise': 0,
                        'method': 'existing',
                        'status': 'skipped'
                    }
        finally:
            conn.close()
        
        # Load embeddings
        embeddings, article_ids = self._load_embeddings()
        
        if len(embeddings) == 0:
            logger.warning("No embeddings found for clustering")
            return {
                'clusters_created': 0,
                'articles_clustered': 0,
                'noise': 0,
                'method': None,
                'status': 'no_embeddings'
            }
        
        logger.info(f"Clustering {len(embeddings)} articles...")
        
        # Try HDBSCAN first
        labels, n_clusters = self._cluster_hdbscan(embeddings)
        
        # Fallback to k-means if HDBSCAN found < 2 clusters
        method = 'hdbscan'
        if n_clusters < 2:
            logger.info("HDBSCAN found < 2 clusters, falling back to k-means")
            labels, n_clusters = self._cluster_kmeans(embeddings)
            method = 'kmeans'
        
        # Count noise points
        noise_count = int(np.sum(labels == -1))
        clustered_count = len(embeddings) - noise_count
        
        # Update database
        self._update_article_clusters(article_ids, labels)
        self._update_clusters_table(labels)
        
        stats = {
            'clusters_created': n_clusters,
            'articles_clustered': clustered_count,
            'noise': noise_count,
            'method': method,
            'status': 'completed'
        }
        
        logger.info(f"Clustering complete: {stats}")
        
        return stats

