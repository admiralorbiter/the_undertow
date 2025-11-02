"""
UMAP 2D projection service.
Projects embeddings to 2D for visualization.
"""
import logging
import numpy as np
import sqlite3
from typing import Tuple, List
import umap
from backend.db import get_db
from backend.config import Config
from backend.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class UMAPService:
    """Service for projecting embeddings to 2D using UMAP."""
    
    def __init__(self):
        """Initialize UMAP service."""
        self.embedding_service = EmbeddingService()
        self.n_neighbors = Config.UMAP_N_NEIGHBORS
        self.min_dist = Config.UMAP_MIN_DIST
        self.metric = Config.UMAP_METRIC
        self.random_state = 42  # For reproducibility
        
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
            
            return embeddings_array, article_ids
            
        finally:
            conn.close()
    
    def project_to_2d(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Project embeddings to 2D using UMAP.
        
        Args:
            embeddings: Embedding vectors (n_samples, n_features)
            
        Returns:
            2D coordinates (n_samples, 2)
        """
        logger.info(f"Running UMAP on {len(embeddings)} embeddings...")
        logger.info(f"Parameters: n_neighbors={self.n_neighbors}, "
                   f"min_dist={self.min_dist}, metric={self.metric}")
        
        # Create UMAP reducer
        reducer = umap.UMAP(
            n_neighbors=self.n_neighbors,
            min_dist=self.min_dist,
            n_components=2,
            metric=self.metric,
            random_state=self.random_state,
            verbose=False
        )
        
        # Fit and transform
        coords_2d = reducer.fit_transform(embeddings)
        
        logger.info(f"UMAP projection complete: shape {coords_2d.shape}")
        
        return coords_2d
    
    def update_article_coordinates(self, article_ids: List[int], coords_2d: np.ndarray):
        """
        Update articles table with UMAP coordinates.
        
        Args:
            article_ids: List of article IDs (same order as coords)
            coords_2d: 2D coordinates (n_samples, 2)
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Update umap_x and umap_y for each article
            updates = []
            for article_id, coords in zip(article_ids, coords_2d):
                x, y = float(coords[0]), float(coords[1])
                updates.append((x, y, article_id))
            
            cursor.executemany("""
                UPDATE articles SET umap_x = ?, umap_y = ? WHERE id = ?
            """, updates)
            
            conn.commit()
            
            logger.info(f"Updated UMAP coordinates for {len(updates)} articles")
            
        except Exception as e:
            logger.error(f"Error updating article coordinates: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def compute_umap_projection(self, force_recompute=False) -> dict:
        """
        Compute UMAP 2D projection for all articles with embeddings.
        
        Args:
            force_recompute: If True, recompute even if coordinates exist
            
        Returns:
            dict with stats: {'points_projected': int, 'status': str}
        """
        logger.info("Computing UMAP 2D projection...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Check if UMAP already computed
            if not force_recompute:
                cursor.execute("""
                    SELECT COUNT(*) FROM articles 
                    WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
                """)
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    logger.info(f"UMAP coordinates already exist for {existing_count} articles")
                    return {
                        'points_projected': existing_count,
                        'status': 'skipped'
                    }
        finally:
            conn.close()
        
        # Load embeddings
        embeddings, article_ids = self._load_embeddings()
        
        if len(embeddings) == 0:
            logger.warning("No embeddings found for UMAP projection")
            return {
                'points_projected': 0,
                'status': 'no_embeddings'
            }
        
        if len(embeddings) < self.n_neighbors:
            logger.warning(f"Not enough embeddings ({len(embeddings)}) for n_neighbors={self.n_neighbors}")
            # Adjust n_neighbors
            adjusted_neighbors = max(2, len(embeddings) - 1)
            logger.info(f"Adjusting n_neighbors to {adjusted_neighbors}")
            self.n_neighbors = adjusted_neighbors
        
        logger.info(f"Projecting {len(embeddings)} embeddings to 2D...")
        
        # Project to 2D
        coords_2d = self.project_to_2d(embeddings)
        
        # Update database
        self.update_article_coordinates(article_ids, coords_2d)
        
        stats = {
            'points_projected': len(coords_2d),
            'status': 'completed'
        }
        
        logger.info(f"UMAP projection complete: {stats}")
        
        return stats

