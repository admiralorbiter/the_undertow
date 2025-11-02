"""
Similarity graph service.
Builds similarity graph using FAISS and computes shared terms.
"""
import logging
import json
import sqlite3
from typing import List, Dict, Set, Tuple
from collections import Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from backend.db import get_db
from backend.config import Config
from backend.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class SimilarityService:
    """Service for building similarity graph and computing shared terms."""
    
    def __init__(self):
        """Initialize similarity service."""
        self.embedding_service = EmbeddingService()
        self.threshold = Config.SIMILARITY_THRESHOLD
        self.knn_k = Config.KNN_K
        
    def _tokenize_text(self, text: str) -> Set[str]:
        """
        Simple tokenization for shared terms extraction.
        
        Args:
            text: Text to tokenize
            
        Returns:
            Set of lowercase tokens (words)
        """
        if not text:
            return set()
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out very short words
        return {w for w in words if len(w) >= 3}
    
    def compute_shared_terms(self, text1: str, text2: str, top_n: int = 10) -> List[str]:
        """
        Compute shared terms between two texts using TF-IDF.
        
        Args:
            text1: First text (title + summary)
            text2: Second text (title + summary)
            top_n: Number of top shared terms to return
            
        Returns:
            List of shared terms (keywords)
        """
        if not text1 or not text2:
            return []
        
        # Combine texts for TF-IDF
        documents = [text1, text2]
        
        try:
            # Use TF-IDF with unigrams and bigrams
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=100,
                stop_words='english',
                min_df=1,
                token_pattern=r'\b\w+\b'
            )
            
            tfidf_matrix = vectorizer.fit_transform(documents)
            
            # Get feature names (terms)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores for each document
            scores1 = tfidf_matrix[0].toarray()[0]
            scores2 = tfidf_matrix[1].toarray()[0]
            
            # Find terms present in both documents (with non-zero TF-IDF)
            shared_terms = []
            for i, term in enumerate(feature_names):
                if scores1[i] > 0 and scores2[i] > 0:
                    # Average TF-IDF score
                    avg_score = (scores1[i] + scores2[i]) / 2
                    shared_terms.append((term, avg_score))
            
            # Sort by average score and return top N
            shared_terms.sort(key=lambda x: x[1], reverse=True)
            return [term for term, _ in shared_terms[:top_n]]
            
        except Exception as e:
            logger.warning(f"Error computing shared terms: {e}")
            # Fallback: simple intersection of tokenized words
            tokens1 = self._tokenize_text(text1)
            tokens2 = self._tokenize_text(text2)
            shared = sorted(tokens1 & tokens2, key=lambda x: len(x), reverse=True)
            return shared[:top_n]
    
    def build_similarity_graph(self, force_recompute=False):
        """
        Build similarity graph by querying FAISS for each article.
        
        For each article, finds top-k neighbors above similarity threshold,
        computes shared terms, and stores in similarities table.
        
        Args:
            force_recompute: If True, recompute even if similarities exist
            
        Returns:
            dict with stats: {'edges_created': int, 'skipped': int, 'errors': int}
        """
        logger.info("Building similarity graph...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        stats = {'edges_created': 0, 'skipped': 0, 'errors': 0}
        
        try:
            # Get all articles with embeddings
            cursor.execute("""
                SELECT a.id, a.title, a.summary
                FROM articles a
                INNER JOIN embeddings e ON a.id = e.article_id
                ORDER BY a.id
            """)
            articles = cursor.fetchall()
            
            if len(articles) == 0:
                logger.warning("No articles with embeddings found")
                return stats
            
            logger.info(f"Processing {len(articles)} articles for similarity graph...")
            
            # Load FAISS index
            faiss_index, article_ids_map = self.embedding_service.load_faiss_index()
            if faiss_index is None:
                logger.error("FAISS index not found. Run step_embeddings first.")
                return stats
            
            # Create reverse mapping: article_id -> FAISS index position
            article_to_index = {}
            if article_ids_map is not None:
                for idx, article_id in enumerate(article_ids_map):
                    article_to_index[int(article_id)] = idx
            
            # Process each article
            processed = 0
            for article_row in articles:
                article_id = article_row['id']
                title = article_row['title'] or ''
                summary = article_row['summary'] or ''
                article_text = f"{title} \n {summary}".strip()
                
                try:
                    # Check if we should skip (if similarities already exist and not forcing)
                    if not force_recompute:
                        cursor.execute("""
                            SELECT COUNT(*) FROM similarities WHERE src_id = ?
                        """, (article_id,))
                        count = cursor.fetchone()[0]
                        if count > 0:
                            stats['skipped'] += 1
                            continue
                    
                    # Query FAISS for similar articles
                    similar_results = self.embedding_service.query_similar(
                        article_id, k=self.knn_k
                    )
                    
                    # Filter by threshold and process
                    edges_to_insert = []
                    
                    for similar_id, cosine_score in similar_results:
                        # Filter by similarity threshold
                        if cosine_score < self.threshold:
                            continue
                        
                        # Get similar article text for shared terms
                        cursor.execute("""
                            SELECT title, summary FROM articles WHERE id = ?
                        """, (similar_id,))
                        similar_row = cursor.fetchone()
                        
                        if not similar_row:
                            continue
                        
                        similar_title = similar_row['title'] or ''
                        similar_summary = similar_row['summary'] or ''
                        similar_text = f"{similar_title} \n {similar_summary}".strip()
                        
                        # Compute shared terms
                        shared_terms = self.compute_shared_terms(
                            article_text, similar_text, top_n=10
                        )
                        
                        # Store edge bidirectionally for easier querying
                        # Store src -> dst
                        edges_to_insert.append({
                            'src_id': article_id,
                            'dst_id': similar_id,
                            'cosine': cosine_score,
                            'shared_entities': json.dumps([]),  # Placeholder for P2 NER
                            'shared_terms': json.dumps(shared_terms)
                        })
                        
                        # Store dst -> src (reverse edge with same similarity)
                        # Note: shared terms are the same, just reversed
                        edges_to_insert.append({
                            'src_id': similar_id,
                            'dst_id': article_id,
                            'cosine': cosine_score,
                            'shared_entities': json.dumps([]),  # Placeholder for P2 NER
                            'shared_terms': json.dumps(shared_terms)
                        })
                    
                    # Batch insert edges
                    if edges_to_insert:
                        # Use INSERT OR IGNORE to avoid duplicate key errors when storing bidirectionally
                        cursor.executemany("""
                            INSERT OR IGNORE INTO similarities 
                            (src_id, dst_id, cosine, shared_entities, shared_terms)
                            VALUES (?, ?, ?, ?, ?)
                        """, [
                            (
                                edge['src_id'],
                                edge['dst_id'],
                                edge['cosine'],
                                edge['shared_entities'],
                                edge['shared_terms']
                            )
                            for edge in edges_to_insert
                        ])
                        
                        stats['edges_created'] += len(edges_to_insert)
                        processed += 1
                        
                        # Commit periodically (every 50 articles)
                        if processed % 50 == 0:
                            conn.commit()
                            logger.info(f"Processed {processed} articles, created {stats['edges_created']} edges...")
                
                except Exception as e:
                    logger.error(f"Error processing article {article_id}: {e}", exc_info=True)
                    stats['errors'] += 1
                    continue
            
            # Final commit
            conn.commit()
            
            logger.info(f"Similarity graph complete: {stats['edges_created']} edges created, "
                       f"{stats['skipped']} skipped, {stats['errors']} errors")
            
        except Exception as e:
            logger.error(f"Error in build_similarity_graph: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
        
        return stats

