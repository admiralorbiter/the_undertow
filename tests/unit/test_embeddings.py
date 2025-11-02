"""
Tests for embedding generation service.
"""
import pytest
import numpy as np
import sqlite3
from pathlib import Path

# Skip tests if dependencies aren't installed
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

if HAS_DEPENDENCIES:
    from backend.services.embeddings import EmbeddingService
    from backend.config import Config

pytestmark = pytest.mark.skipif(not HAS_DEPENDENCIES, reason="ML dependencies not installed")


class TestEmbeddingService:
    """Test embedding generation and FAISS index building."""
    
    def test_vector_to_blob_and_back(self):
        """Test conversion between numpy array and BLOB."""
        service = EmbeddingService()
        
        # Create test vector
        original = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        
        # Convert to blob and back
        blob = service._vector_to_blob(original)
        restored = service._blob_to_vector(blob)
        
        np.testing.assert_array_almost_equal(original, restored)
        assert restored.dtype == np.float32
    
    def test_generate_embeddings_for_sample_articles(self, temp_db, monkeypatch):
        """Test generating embeddings for sample articles."""
        from backend.config import Config
        
        # Insert test articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        test_articles = [
            ('Test Article 1', 'Summary of test article 1', 'https://example.com/1', 'example.com', '2025-02-10', '2025-02'),
            ('Test Article 2', 'Summary of test article 2', 'https://example.com/2', 'example.com', '2025-02-11', '2025-02'),
        ]
        
        for title, summary, url, outlet, date, date_bin in test_articles:
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, summary, url, outlet, date, date_bin))
        
        conn.commit()
        conn.close()
        
        # Generate embeddings
        service = EmbeddingService()
        stats = service.generate_embeddings(force_recompute=False)
        
        # Verify embeddings were created
        assert stats['processed'] >= 2
        assert stats['errors'] == 0
        
        # Verify embeddings in database
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        count = cursor.fetchone()[0]
        assert count >= 2
        
        # Verify embedding dimensions
        cursor.execute("SELECT vec FROM embeddings LIMIT 1")
        row = cursor.fetchone()
        if row:
            vector = service._blob_to_vector(row['vec'])
            assert vector.shape[0] == Config.EMBEDDING_DIM
            assert vector.dtype == np.float32
        
        conn.close()
    
    def test_build_faiss_index(self, temp_db, monkeypatch):
        """Test building FAISS index."""
        from backend.config import Config
        
        # First, generate some embeddings
        service = EmbeddingService()
        
        # Insert test articles and generate embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test', 'Summary', 'https://example.com/test', 'example.com', '2025-02-10', '2025-02'))
        article_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate embedding
        stats = service.generate_embeddings(force_recompute=False)
        assert stats['processed'] >= 1
        
        # Build FAISS index
        index_stats = service.build_faiss_index(force_rebuild=True)
        
        assert index_stats['index_built'] is True
        assert index_stats['vector_count'] >= 1
        assert index_stats['dim'] == Config.EMBEDDING_DIM
        
        # Verify index file exists
        index_path = Path(Config.FAISS_INDEX_PATH)
        assert index_path.exists()
        
        # Verify vector_meta updated
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT count, dim FROM vector_meta WHERE version = 1")
        meta = cursor.fetchone()
        assert meta is not None
        assert meta['count'] >= 1
        assert meta['dim'] == Config.EMBEDDING_DIM
        conn.close()
    
    def test_load_faiss_index(self, temp_db, monkeypatch):
        """Test loading FAISS index."""
        from backend.config import Config
        
        service = EmbeddingService()
        
        # Generate embeddings and build index
        service.generate_embeddings(force_recompute=False)
        service.build_faiss_index(force_rebuild=True)
        
        # Load index
        index, article_ids = service.load_faiss_index()
        
        assert index is not None
        assert article_ids is not None
        assert index.ntotal > 0
    
    def test_query_similar(self, temp_db, monkeypatch):
        """Test querying FAISS for similar articles."""
        from backend.config import Config
        
        service = EmbeddingService()
        
        # Insert and generate embeddings for multiple articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        articles = [
            ('Python Programming', 'Learn Python programming', 'https://example.com/python', 'example.com', '2025-02-10', '2025-02'),
            ('Python Tutorial', 'Python tutorial for beginners', 'https://example.com/tutorial', 'example.com', '2025-02-11', '2025-02'),
            ('JavaScript Guide', 'JavaScript programming guide', 'https://example.com/js', 'example.com', '2025-02-12', '2025-02'),
        ]
        
        for title, summary, url, outlet, date, date_bin in articles:
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, summary, url, outlet, date, date_bin))
        
        conn.commit()
        conn.close()
        
        # Generate embeddings
        service.generate_embeddings(force_recompute=False)
        
        # Build index
        service.build_faiss_index(force_rebuild=True)
        
        # Query for similar articles to the first one
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM articles WHERE title = 'Python Programming'")
        article_id = cursor.fetchone()[0]
        conn.close()
        
        # Query similar
        results = service.query_similar(article_id, k=2)
        
        # Should find at least the other Python article
        assert len(results) > 0
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
        assert all(isinstance(r[1], (int, float)) for r in results)  # similarity score

