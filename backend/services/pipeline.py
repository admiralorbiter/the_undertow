"""
NLP & Analytics Pipeline Orchestrator

Runs the 9-step pipeline (steps 3-9) to compute embeddings, similarities, clusters, UMAP, etc.
Steps 1-2 (ingest and FTS) are handled separately during CSV ingestion.
"""
import logging
from backend.db import get_db
from backend.config import Config

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates the NLP & Analytics pipeline (steps 3-9).
    
    Steps:
    3. Embeddings - Generate sentence embeddings for all articles
    4. Similarity Graph - Build similarity graph using FAISS
    5. Clustering - Cluster articles using HDBSCAN
    6. UMAP - Project to 2D for visualization
    7. Keyword/Labeling - Generate cluster labels using KeyBERT
    8. NER - Extract named entities (P2, but structure here)
    9. Storylines - Group near-duplicate articles (P2)
    """
    
    def __init__(self):
        """Initialize pipeline runner."""
        self.steps_completed = set()
        
    def step_embeddings(self, force_recompute=False):
        """
        Step 3: Generate embeddings for all articles.
        
        Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim)
        Text: title + " \n " + summary
        Persists: float32 vectors to embeddings table, builds FAISS index
        
        Args:
            force_recompute: If True, recompute even if embeddings exist
            
        Returns:
            dict with stats: {'processed': int, 'skipped': int, 'errors': int, 'index_built': bool}
        """
        logger.info("Step 3: Generating embeddings...")
        
        from backend.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        
        # Generate embeddings
        stats = service.generate_embeddings(force_recompute=force_recompute)
        
        # Build FAISS index
        index_stats = service.build_faiss_index(force_rebuild=force_recompute)
        
        stats.update(index_stats)
        stats['status'] = 'completed'
        
        if stats['processed'] > 0 or index_stats.get('index_built', False):
            self.steps_completed.add(3)
        
        return stats
    
    def step_similarity_graph(self, force_recompute=False):
        """
        Step 4: Build similarity graph.
        
        For each article, find top-k neighbors above similarity threshold.
        Computes shared entities/terms as evidence (when available).
        
        Args:
            force_recompute: If True, recompute even if similarities exist
            
        Returns:
            dict with stats: {'edges_created': int, 'skipped': int, 'errors': int}
        """
        logger.info("Step 4: Building similarity graph...")
        
        from backend.services.similarity import SimilarityService
        
        service = SimilarityService()
        stats = service.build_similarity_graph(force_recompute=force_recompute)
        
        stats['status'] = 'completed'
        
        if stats['edges_created'] > 0:
            self.steps_completed.add(4)
        
        return stats
    
    def step_clustering(self, force_recompute=False):
        """
        Step 5: Cluster articles using HDBSCAN.
        
        Uses HDBSCAN with cosine metric, min_cluster_size=8.
        Falls back to k-means with silhouette score if HDBSCAN fails.
        Updates articles.cluster_id and clusters table.
        
        Args:
            force_recompute: If True, recompute even if clusters exist
            
        Returns:
            dict with stats: {'clusters_created': int, 'articles_clustered': int, 'noise': int, 'method': str}
        """
        logger.info("Step 5: Clustering articles...")
        
        from backend.services.clustering import ClusteringService
        
        service = ClusteringService()
        stats = service.cluster_articles(force_recompute=force_recompute)
        
        if stats.get('status') != 'skipped' and stats.get('clusters_created', 0) > 0:
            self.steps_completed.add(5)
        
        return stats
    
    def step_umap(self, force_recompute=False):
        """
        Step 6: UMAP 2D projection.
        
        Projects embeddings to 2D for visualization.
        Stores x, y coordinates in articles table (umap_x, umap_y).
        
        Args:
            force_recompute: If True, recompute even if UMAP coords exist
            
        Returns:
            dict with stats: {'points_projected': int, 'status': str}
        """
        logger.info("Step 6: Computing UMAP projection...")
        
        from backend.services.umap_projection import UMAPService
        
        service = UMAPService()
        stats = service.compute_umap_projection(force_recompute=force_recompute)
        
        if stats.get('status') != 'skipped' and stats.get('points_projected', 0) > 0:
            self.steps_completed.add(6)
        
        return stats
    
    def step_keywords(self, force_recompute=False):
        """
        Step 7: Generate cluster labels using KeyBERT.
        
        For each cluster, extracts top keywords and creates labels.
        Updates clusters.label field.
        
        Args:
            force_recompute: If True, recompute even if labels exist
            
        Returns:
            dict with stats: {'clusters_labeled': int, 'errors': int, 'status': str}
        """
        logger.info("Step 7: Generating cluster labels...")
        
        from backend.services.labeling import LabelingService
        
        service = LabelingService()
        stats = service.label_all_clusters(force_recompute=force_recompute)
        
        if stats.get('status') != 'skipped' and stats.get('clusters_labeled', 0) > 0:
            self.steps_completed.add(7)
        
        return stats
    
    def step_ner(self, force_recompute=False):
        """
        Step 8: Named Entity Recognition.
        
        Extracts PERSON, ORG, GPE, LOC entities from articles.
        Populates entities and article_entities tables.
        
        Args:
            force_recompute: If True, recompute even if entities exist
            
        Returns:
            dict with stats: {'articles_processed': int, 'entities_found': int}
        """
        logger.info("Step 8: Extracting named entities...")
        
        from backend.services.ner import NERService
        
        service = NERService()
        stats = service.extract_entities(force_recompute=force_recompute)
        
        if stats.get('articles_processed', 0) > 0:
            self.steps_completed.add(8)
        
        return stats
    
    def step_entity_roles(self, force_recompute=False):
        """
        Step 8b: Entity role classification.
        
        Classifies entity roles (protagonist, antagonist, subject, adjudicator)
        in articles based on contextual patterns.
        
        Args:
            force_recompute: If True, recompute even if roles exist
            
        Returns:
            dict with stats: {'roles_classified': int}
        """
        logger.info("Step 8b: Classifying entity roles...")
        
        from backend.services.ner import NERService
        
        service = NERService()
        stats = service.classify_entity_roles(force_recompute=force_recompute)
        
        if stats.get('roles_classified', 0) > 0:
            # Add to completed steps (use 8.5 as a float to distinguish from 8)
            # Actually, let's just track it as part of step 8
            pass
        
        return stats
    
    def step_storylines(self, force_recompute=False):
        """
        Step 9: Storyline threading (multi-tier).
        
        Builds storylines using Union-Find grouping across three tiers:
        - Tier 1: Near-duplicates (cosine >= 0.85, days <= 3)
        - Tier 2: Continuations (0.65 <= cosine < 0.85, days <= 7)
        - Tier 3: Related (0.50 <= cosine < 0.65, shared entities >= 2)
        
        Args:
            force_recompute: If True, recompute even if storylines exist
            
        Returns:
            dict with stats: {'storylines_created': int, 'articles_grouped': int}
        """
        logger.info("Step 9: Building storylines...")
        
        from backend.services.storylines import StorylineService
        
        service = StorylineService()
        stats = service.build_storylines(force_recompute=force_recompute)
        
        if stats.get('storylines_created', 0) > 0:
            self.steps_completed.add(9)
        
        return stats
    
    def step_monitoring(self, force_recompute=False):
        """
        Step 10: Monitoring and anomaly detection.
        
        Runs detection algorithms to identify:
        - Topic surges
        - Story reactivations
        - New actor emergence
        
        Args:
            force_recompute: If True, run even if alerts exist
            
        Returns:
            dict with stats: {'alerts_created': int, 'surges': int, 'reactivations': int, 'new_actors': int}
        """
        logger.info("Step 10: Running monitoring detections...")
        
        from backend.services.monitoring import MonitoringService
        
        service = MonitoringService()
        stats = service.run_detections()
        
        if stats.get('alerts_created', 0) > 0:
            self.steps_completed.add(10)
        
        return stats
    
    def run_full_pipeline(self, start_from_step=3, force_recompute=False):
        """
        Run the full pipeline (steps 3-9).
        
        Args:
            start_from_step: Which step to start from (3-9)
            force_recompute: If True, recompute even if step was already completed
            
        Returns:
            dict with results from each step
        """
        logger.info(f"Running full pipeline starting from step {start_from_step}")
        
        results = {}
        steps = {
            3: self.step_embeddings,
            4: self.step_similarity_graph,
            5: self.step_clustering,
            6: self.step_umap,
            7: self.step_keywords,
            8: self.step_ner,
            9: self.step_storylines,
            10: self.step_monitoring
        }
        
        for step_num in range(start_from_step, 11):
            if step_num in steps:
                try:
                    result = steps[step_num](force_recompute=force_recompute)
                    results[f'step_{step_num}'] = result
                    if result.get('status') != 'not_implemented':
                        self.steps_completed.add(step_num)
                except Exception as e:
                    logger.error(f"Error in step {step_num}: {e}", exc_info=True)
                    results[f'step_{step_num}'] = {'status': 'error', 'error': str(e)}
        
        return results
    
    def get_pipeline_status(self):
        """
        Get status of pipeline execution.
        
        Returns:
            dict with status info:
            {
                'steps_completed': [list of step numbers],
                'embeddings_count': int,
                'similarities_count': int,
                'clusters_count': int,
                'articles_with_umap': int,
                'clusters_labeled': int,
                'has_faiss_index': bool
            }
        """
        conn = get_db()
        cursor = conn.cursor()
        
        status = {
            'steps_completed': list(self.steps_completed),
            'embeddings_count': 0,
            'similarities_count': 0,
            'clusters_count': 0,
            'articles_with_umap': 0,
            'clusters_labeled': 0,
            'storylines_count': 0,
            'alerts_count': 0,
            'has_faiss_index': False
        }
        
        try:
            # Count embeddings
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            status['embeddings_count'] = cursor.fetchone()[0]
            
            # Count similarities
            cursor.execute("SELECT COUNT(*) FROM similarities")
            status['similarities_count'] = cursor.fetchone()[0]
            
            # Count clusters
            cursor.execute("SELECT COUNT(*) FROM clusters")
            status['clusters_count'] = cursor.fetchone()[0]
            
            # Count articles with UMAP coords
            cursor.execute("SELECT COUNT(*) FROM articles WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL")
            status['articles_with_umap'] = cursor.fetchone()[0]
            
            # Count clusters with labels
            cursor.execute("SELECT COUNT(*) FROM clusters WHERE label IS NOT NULL AND label != ''")
            status['clusters_labeled'] = cursor.fetchone()[0]
            
            # Count storylines
            cursor.execute("SELECT COUNT(*) FROM storylines")
            status['storylines_count'] = cursor.fetchone()[0]
            
            # Count alerts
            cursor.execute("SELECT COUNT(*) FROM alerts")
            status['alerts_count'] = cursor.fetchone()[0]
            
            # Check if FAISS index exists
            from pathlib import Path
            status['has_faiss_index'] = Path(Config.FAISS_INDEX_PATH).exists()
            
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
        finally:
            conn.close()
        
        return status

