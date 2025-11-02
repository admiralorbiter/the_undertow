"""
Cluster labeling service.
Generates human-readable labels for clusters using KeyBERT.
"""
import logging
import sqlite3
from typing import List, Dict
from keybert import KeyBERT
from backend.db import get_db
from backend.config import Config

logger = logging.getLogger(__name__)


class LabelingService:
    """Service for generating cluster labels using KeyBERT."""
    
    def __init__(self):
        """Initialize labeling service."""
        self.keybert_model = None
        self.top_n = Config.KEYBERT_TOP_N  # Extract top N keywords
        self.top_k_labels = Config.KEYBERT_TOP_K_LABELS  # Use top K for final label
        
    def _load_keybert(self):
        """Load KeyBERT model (with caching)."""
        if self.keybert_model is None:
            logger.info("Loading KeyBERT model...")
            try:
                # Use all-MiniLM-L6-v2 for consistency with embeddings
                # KeyBERT can use a different model, but we'll use the same one
                from sentence_transformers import SentenceTransformer
                from pathlib import Path
                
                cache_dir = Path(Config.MODEL_CACHE_DIR)
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                sentence_model = SentenceTransformer(
                    Config.EMBEDDING_MODEL,
                    cache_folder=str(cache_dir)
                )
                
                self.keybert_model = KeyBERT(model=sentence_model)
                logger.info("KeyBERT model loaded")
            except Exception as e:
                logger.error(f"Error loading KeyBERT model: {e}", exc_info=True)
                raise
        return self.keybert_model
    
    def _get_cluster_articles(self, cluster_id: int) -> List[Dict]:
        """
        Get all articles for a cluster.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            List of article dicts with title and summary
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT title, summary
                FROM articles
                WHERE cluster_id = ?
            """, (cluster_id,))
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'title': row['title'] or '',
                    'summary': row['summary'] or ''
                })
            
            return articles
            
        finally:
            conn.close()
    
    def _combine_cluster_text(self, articles: List[Dict]) -> str:
        """
        Combine all article titles and summaries for a cluster.
        
        Args:
            articles: List of article dicts
            
        Returns:
            Combined text string
        """
        texts = []
        for article in articles:
            title = article.get('title', '').strip()
            summary = article.get('summary', '').strip()
            
            if title:
                texts.append(title)
            if summary:
                texts.append(summary)
        
        # Join with spaces
        combined = ' '.join(texts)
        return combined
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text using KeyBERT.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keyword strings
        """
        if not text or len(text.strip()) < 10:
            return []
        
        try:
            model = self._load_keybert()
            
            # Extract keywords (returns list of tuples: (keyword, score))
            keywords_with_scores = model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # Unigrams and bigrams
                top_n=self.top_n,
                use_mmr=True,  # Use Maximal Marginal Relevance for diversity
                diversity=0.5
            )
            
            # Extract just the keywords (drop scores)
            keywords = [kw[0] for kw in keywords_with_scores]
            
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}", exc_info=True)
            return []
    
    def _create_label(self, keywords: List[str]) -> str:
        """
        Create a readable label from keywords.
        
        Takes top K keywords and joins them nicely.
        
        Args:
            keywords: List of keywords
            
        Returns:
            Human-readable label string
        """
        if not keywords:
            return "Unlabeled"
        
        # Take top K keywords
        top_keywords = keywords[:self.top_k_labels]
        
        # Join with commas or " & " for better readability
        if len(top_keywords) == 1:
            return top_keywords[0]
        elif len(top_keywords) == 2:
            return f"{top_keywords[0]} & {top_keywords[1]}"
        else:
            # For 3+, join first with commas, last with " & "
            return ", ".join(top_keywords[:-1]) + f" & {top_keywords[-1]}"
    
    def label_cluster(self, cluster_id: int) -> str:
        """
        Generate a label for a single cluster.
        
        Args:
            cluster_id: Cluster ID to label
            
        Returns:
            Label string
        """
        # Get cluster articles
        articles = self._get_cluster_articles(cluster_id)
        
        if len(articles) == 0:
            logger.warning(f"No articles found for cluster {cluster_id}")
            return "Empty Cluster"
        
        # Combine article texts
        combined_text = self._combine_cluster_text(articles)
        
        if not combined_text or len(combined_text.strip()) < 10:
            logger.warning(f"Cluster {cluster_id} has insufficient text for labeling")
            return f"Cluster {cluster_id}"
        
        # Extract keywords
        keywords = self._extract_keywords(combined_text)
        
        # Create label
        label = self._create_label(keywords)
        
        logger.info(f"Generated label for cluster {cluster_id}: '{label}'")
        
        return label
    
    def label_all_clusters(self, force_recompute=False) -> Dict:
        """
        Generate labels for all clusters.
        
        Args:
            force_recompute: If True, recompute even if labels exist
            
        Returns:
            dict with stats: {'clusters_labeled': int, 'status': str}
        """
        logger.info("Generating labels for all clusters...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Get all clusters
            if force_recompute:
                cursor.execute("SELECT id FROM clusters ORDER BY id")
            else:
                # Only get clusters without labels
                cursor.execute("SELECT id FROM clusters WHERE label IS NULL ORDER BY id")
            
            cluster_ids = [row['id'] for row in cursor.fetchall()]
            
            if len(cluster_ids) == 0:
                logger.info("No clusters need labeling")
                return {
                    'clusters_labeled': 0,
                    'status': 'skipped'
                }
            
            logger.info(f"Labeling {len(cluster_ids)} clusters...")
            
            # Label each cluster
            labeled_count = 0
            errors = 0
            
            for cluster_id in cluster_ids:
                try:
                    label = self.label_cluster(cluster_id)
                    
                    # Update cluster label
                    cursor.execute("""
                        UPDATE clusters SET label = ? WHERE id = ?
                    """, (label, cluster_id))
                    
                    labeled_count += 1
                    
                except Exception as e:
                    logger.error(f"Error labeling cluster {cluster_id}: {e}", exc_info=True)
                    errors += 1
                    continue
            
            conn.commit()
            
            stats = {
                'clusters_labeled': labeled_count,
                'errors': errors,
                'status': 'completed'
            }
            
            logger.info(f"Cluster labeling complete: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in label_all_clusters: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

