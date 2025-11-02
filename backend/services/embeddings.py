"""
Embedding generation service.
Generates sentence embeddings using sentence-transformers and builds FAISS index.
"""
import logging
import numpy as np
import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
import faiss
from backend.db import get_db
from backend.config import Config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating article embeddings and managing FAISS index."""
    
    def __init__(self):
        """Initialize embedding service."""
        self.model = None
        self.model_name = Config.EMBEDDING_MODEL
        self.dim = Config.EMBEDDING_DIM
        
    def _load_model(self):
        """Load sentence-transformers model (with caching)."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            cache_dir = Path(Config.MODEL_CACHE_DIR)
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Load model with cache directory
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=str(cache_dir)
            )
            logger.info(f"Model loaded: {self.model_name}")
        return self.model
    
    def _vector_to_blob(self, vector: np.ndarray) -> bytes:
        """Convert numpy array to BLOB for SQLite storage."""
        # Ensure float32 and contiguous
        vector = np.ascontiguousarray(vector.astype(np.float32))
        return vector.tobytes()
    
    def _blob_to_vector(self, blob: bytes) -> np.ndarray:
        """Convert BLOB to numpy array."""
        return np.frombuffer(blob, dtype=np.float32)
    
    def generate_embeddings(self, force_recompute=False, batch_size=50):
        """
        Generate embeddings for all articles without embeddings.
        
        Args:
            force_recompute: If True, recompute even if embedding exists
            batch_size: Number of articles to process in each batch
            
        Returns:
            dict with stats: {'processed': int, 'skipped': int, 'errors': int}
        """
        logger.info("Generating embeddings for articles...")
        
        model = self._load_model()
        conn = get_db()
        cursor = conn.cursor()
        
        stats = {'processed': 0, 'skipped': 0, 'errors': 0}
        
        try:
            # Get articles that need embeddings
            if force_recompute:
                cursor.execute("""
                    SELECT id, title, summary FROM articles
                    ORDER BY id
                """)
            else:
                cursor.execute("""
                    SELECT a.id, a.title, a.summary
                    FROM articles a
                    LEFT JOIN embeddings e ON a.id = e.article_id
                    WHERE e.article_id IS NULL
                    ORDER BY a.id
                """)
            
            articles = cursor.fetchall()
            total = len(articles)
            
            if total == 0:
                logger.info("No articles need embeddings")
                return stats
            
            logger.info(f"Processing {total} articles in batches of {batch_size}")
            
            # Process in batches
            for i in range(0, total, batch_size):
                batch = articles[i:i + batch_size]
                
                # Prepare texts for embedding
                texts = []
                article_ids = []
                for row in batch:
                    title = row['title'] or ''
                    summary = row['summary'] or ''
                    # Combine as specified: title + " \n " + summary
                    text = f"{title} \n {summary}".strip()
                    if text:  # Skip empty texts
                        texts.append(text)
                        article_ids.append(row['id'])
                
                if not texts:
                    continue
                
                try:
                    # Generate embeddings
                    logger.info(f"Generating embeddings for batch {i//batch_size + 1} ({len(texts)} articles)...")
                    embeddings = model.encode(
                        texts,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        normalize_embeddings=True  # Normalize for cosine similarity
                    )
                    
                    # Store embeddings in database
                    for article_id, embedding in zip(article_ids, embeddings):
                        try:
                            blob = self._vector_to_blob(embedding)
                            cursor.execute("""
                                INSERT OR REPLACE INTO embeddings (article_id, vec)
                                VALUES (?, ?)
                            """, (article_id, blob))
                            stats['processed'] += 1
                        except sqlite3.Error as e:
                            logger.error(f"Error storing embedding for article {article_id}: {e}")
                            stats['errors'] += 1
                    
                    conn.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing batch: {e}", exc_info=True)
                    stats['errors'] += len(article_ids)
            
            logger.info(f"Embeddings generation complete: {stats['processed']} processed, "
                       f"{stats['skipped']} skipped, {stats['errors']} errors")
            
        except Exception as e:
            logger.error(f"Error in generate_embeddings: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
        
        return stats
    
    def build_faiss_index(self, force_rebuild=False):
        """
        Build or update FAISS index from embeddings in database.
        
        Uses IndexFlatIP (inner product) with normalized vectors for cosine similarity.
        
        Args:
            force_rebuild: If True, rebuild index even if it exists
            
        Returns:
            dict with stats: {'index_built': bool, 'vector_count': int, 'dim': int}
        """
        logger.info("Building FAISS index...")
        
        index_path = Path(Config.FAISS_INDEX_PATH)
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Check if index exists and is up to date
            if not force_rebuild and index_path.exists():
                # Get current count from database
                cursor.execute("SELECT COUNT(*) FROM embeddings")
                db_count = cursor.fetchone()[0]
                
                # Check vector_meta
                cursor.execute("SELECT count FROM vector_meta WHERE version = 1")
                meta_row = cursor.fetchone()
                
                if meta_row and meta_row['count'] == db_count:
                    logger.info(f"FAISS index exists and is up to date ({db_count} vectors)")
                    return {
                        'index_built': False,
                        'vector_count': db_count,
                        'dim': self.dim,
                        'message': 'Index already exists and is current'
                    }
            
            # Load all embeddings from database
            cursor.execute("SELECT article_id, vec FROM embeddings ORDER BY article_id")
            rows = cursor.fetchall()
            
            if len(rows) == 0:
                logger.warning("No embeddings found in database")
                return {
                    'index_built': False,
                    'vector_count': 0,
                    'dim': self.dim,
                    'message': 'No embeddings to index'
                }
            
            # Convert BLOBs to numpy array
            vectors = []
            article_ids = []
            
            for row in rows:
                vector = self._blob_to_vector(row['vec'])
                vectors.append(vector)
                article_ids.append(row['article_id'])
            
            vectors_array = np.array(vectors, dtype=np.float32)
            
            # Ensure vectors are normalized (for cosine similarity via inner product)
            faiss.normalize_L2(vectors_array)
            
            # Create FAISS index (IndexFlatIP for inner product with normalized vectors = cosine similarity)
            index = faiss.IndexFlatIP(self.dim)
            index.add(vectors_array)
            
            # Save index
            index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(index_path))
            
            logger.info(f"FAISS index built: {len(vectors)} vectors, dimension {self.dim}")
            
            # Save article_id mapping (for lookup)
            # Store as separate file: article_id -> index position
            mapping_path = Path(Config.FAISS_INDEX_PATH).parent / 'faiss_mapping.npy'
            np.save(mapping_path, np.array(article_ids, dtype=np.int32))
            
            # Update vector_meta table
            cursor.execute("""
                INSERT OR REPLACE INTO vector_meta (version, dim, count, updated_at)
                VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            """, (self.dim, len(vectors)))
            conn.commit()
            
            return {
                'index_built': True,
                'vector_count': len(vectors),
                'dim': self.dim,
                'index_path': str(index_path)
            }
            
        except Exception as e:
            logger.error(f"Error building FAISS index: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def load_faiss_index(self):
        """
        Load FAISS index from disk.
        
        Returns:
            tuple: (faiss.Index, np.ndarray of article_ids) or (None, None) if not found
        """
        index_path = Path(Config.FAISS_INDEX_PATH)
        mapping_path = index_path.parent / 'faiss_mapping.npy'
        
        if not index_path.exists():
            return None, None
        
        try:
            index = faiss.read_index(str(index_path))
            
            # Load article_id mapping
            article_ids = None
            if mapping_path.exists():
                article_ids = np.load(mapping_path)
            
            return index, article_ids
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}", exc_info=True)
            return None, None
    
    def query_similar(self, article_id: int, k: int = 20) -> List[Tuple[int, float]]:
        """
        Query FAISS index for similar articles.
        
        Args:
            article_id: ID of article to find similarities for
            k: Number of similar articles to return
            
        Returns:
            List of (article_id, similarity_score) tuples
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Get embedding for this article
            cursor.execute("SELECT vec FROM embeddings WHERE article_id = ?", (article_id,))
            row = cursor.fetchone()
            
            if not row:
                return []
            
            # Load FAISS index
            index, article_ids_map = self.load_faiss_index()
            if index is None:
                return []
            
            # Convert article embedding to vector
            query_vector = self._blob_to_vector(row['vec']).reshape(1, -1)
            faiss.normalize_L2(query_vector)  # Normalize for cosine similarity
            
            # Query index
            distances, indices = index.search(query_vector, k + 1)  # +1 to exclude self
            
            # Map indices back to article_ids
            results = []
            for i, dist in zip(indices[0], distances[0]):
                if i < 0:  # Invalid index
                    continue
                if article_ids_map is not None and i < len(article_ids_map):
                    similar_id = int(article_ids_map[i])
                    if similar_id != article_id:  # Exclude self
                        # Inner product with normalized vectors = cosine similarity
                        results.append((similar_id, float(dist)))
                elif article_ids_map is None:
                    # Fallback: assume indices are article_ids (if no mapping file)
                    # This shouldn't happen, but handle gracefully
                    logger.warning("No article_ids mapping found, cannot map FAISS indices")
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying FAISS for article {article_id}: {e}", exc_info=True)
            return []
        finally:
            conn.close()

