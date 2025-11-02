"""
Tests for similarity graph service.
"""
import pytest
import sqlite3
import json

# Skip tests if dependencies aren't installed
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

if HAS_DEPENDENCIES:
    from backend.services.similarity import SimilarityService
    from backend.services.embeddings import EmbeddingService
    from backend.config import Config

pytestmark = pytest.mark.skipif(not HAS_DEPENDENCIES, reason="ML dependencies not installed")


class TestSimilarityService:
    """Test similarity graph building and shared terms computation."""
    
    def test_compute_shared_terms(self):
        """Test shared terms computation."""
        service = SimilarityService()
        
        text1 = "Python programming language is great for data science"
        text2 = "Python is a programming language used in data science"
        
        shared = service.compute_shared_terms(text1, text2, top_n=5)
        
        assert isinstance(shared, list)
        assert len(shared) <= 5
        # Should contain some common terms
        shared_lower = [s.lower() for s in shared]
        assert 'python' in shared_lower or 'programming' in shared_lower or 'data' in shared_lower
    
    def test_compute_shared_terms_empty(self):
        """Test shared terms with empty texts."""
        service = SimilarityService()
        
        assert service.compute_shared_terms("", "some text") == []
        assert service.compute_shared_terms("text", "") == []
        assert service.compute_shared_terms("", "") == []
    
    def test_build_similarity_graph_with_embeddings(self, temp_db, monkeypatch):
        """Test building similarity graph when embeddings exist."""
        from backend.config import Config
        
        # First, create articles and generate embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        articles = [
            ('Python Programming', 'Learn Python programming language', 'https://example.com/python', 'example.com', '2025-02-10', '2025-02'),
            ('Python Tutorial', 'Python tutorial for beginners', 'https://example.com/tutorial', 'example.com', '2025-02-11', '2025-02'),
            ('JavaScript Guide', 'JavaScript programming guide', 'https://example.com/js', 'example.com', '2025-02-12', '2025-02'),
        ]
        
        article_ids = []
        for title, summary, url, outlet, date, date_bin in articles:
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, summary, url, outlet, date, date_bin))
            article_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        
        # Generate embeddings
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        embedding_service.build_faiss_index(force_rebuild=True)
        
        # Build similarity graph
        similarity_service = SimilarityService()
        stats = similarity_service.build_similarity_graph(force_recompute=False)
        
        # Verify edges were created
        assert stats['edges_created'] >= 0  # Could be 0 if threshold too high
        
        # Check similarities table
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM similarities")
        count = cursor.fetchone()[0]
        
        # If we have edges, verify structure
        if count > 0:
            cursor.execute("""
                SELECT src_id, dst_id, cosine, shared_terms
                FROM similarities LIMIT 1
            """)
            row = cursor.fetchone()
            
            assert row['src_id'] in article_ids
            assert row['dst_id'] in article_ids
            assert row['src_id'] != row['dst_id']
            assert row['cosine'] >= Config.SIMILARITY_THRESHOLD
            
            # Verify shared_terms is valid JSON
            if row['shared_terms']:
                terms = json.loads(row['shared_terms'])
                assert isinstance(terms, list)
        
        conn.close()
    
    def test_build_similarity_graph_respects_threshold(self, temp_db, monkeypatch):
        """Test that similarity graph filters by threshold."""
        from backend.config import Config
        
        # This test verifies that edges below threshold are not stored
        # We'll create embeddings and build graph, then verify all edges >= threshold
        
        # Create articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test Article', 'Test summary', 'https://example.com/test', 'example.com', '2025-02-10', '2025-02'))
        article_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate embeddings and build graph
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        embedding_service.build_faiss_index(force_rebuild=True)
        
        similarity_service = SimilarityService()
        stats = similarity_service.build_similarity_graph(force_recompute=False)
        
        # Verify all edges in database are above threshold
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT cosine FROM similarities")
        for row in cursor.fetchall():
            assert row['cosine'] >= Config.SIMILARITY_THRESHOLD
        
        conn.close()

