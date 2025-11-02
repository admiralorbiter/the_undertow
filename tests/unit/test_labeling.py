"""
Tests for cluster labeling service.
"""
import pytest
import sqlite3

# Skip tests if dependencies aren't installed
try:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

if HAS_DEPENDENCIES:
    from backend.services.labeling import LabelingService
    from backend.services.embeddings import EmbeddingService
    from backend.services.clustering import ClusteringService
    from backend.config import Config

pytestmark = pytest.mark.skipif(not HAS_DEPENDENCIES, reason="ML dependencies not installed")


class TestLabelingService:
    """Test cluster labeling functionality."""
    
    def test_get_cluster_articles(self, temp_db, monkeypatch):
        """Test retrieving articles for a cluster."""
        from backend.config import Config
        
        # Create cluster and articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)", 
                      (1, None, 2, 0.0))
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Python Article', 'Python summary', 'https://example.com/1', 'example.com', '2025-02-10', '2025-02', 1))
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('JavaScript Article', 'JavaScript summary', 'https://example.com/2', 'example.com', '2025-02-11', '2025-02', 1))
        
        conn.commit()
        conn.close()
        
        # Get cluster articles
        service = LabelingService()
        articles = service._get_cluster_articles(1)
        
        assert len(articles) == 2
        assert any(a['title'] == 'Python Article' for a in articles)
        assert any(a['title'] == 'JavaScript Article' for a in articles)
    
    def test_combine_cluster_text(self):
        """Test combining article texts."""
        service = LabelingService()
        
        articles = [
            {'title': 'Python Programming', 'summary': 'Learn Python'},
            {'title': 'Python Tutorial', 'summary': 'Python basics'},
        ]
        
        combined = service._combine_cluster_text(articles)
        
        assert 'Python Programming' in combined
        assert 'Learn Python' in combined
        assert 'Python Tutorial' in combined
        assert 'Python basics' in combined
    
    def test_combine_cluster_text_empty(self):
        """Test combining empty articles."""
        service = LabelingService()
        
        articles = []
        combined = service._combine_cluster_text(articles)
        assert combined == ''
        
        articles = [{'title': '', 'summary': ''}]
        combined = service._combine_cluster_text(articles)
        assert combined == ''
    
    def test_create_label(self):
        """Test creating label from keywords."""
        service = LabelingService()
        
        # Single keyword
        label = service._create_label(['Python'])
        assert label == 'Python'
        
        # Two keywords
        label = service._create_label(['Python', 'Programming'])
        assert label == 'Python & Programming'
        
        # Three keywords
        label = service._create_label(['Python', 'Programming', 'Tutorial'])
        assert label == 'Python, Programming & Tutorial'
        
        # More than top_k
        label = service._create_label(['Python', 'Programming', 'Tutorial', 'Guide', 'Book'])
        assert label == 'Python, Programming & Tutorial'  # Top 3
        
        # Empty keywords
        label = service._create_label([])
        assert label == 'Unlabeled'
    
    def test_label_cluster(self, temp_db, monkeypatch):
        """Test labeling a single cluster."""
        from backend.config import Config
        
        # Create cluster with articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)", 
                      (1, None, 2, 0.0))
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Python Programming Guide', 'Comprehensive guide to Python programming language', 
              'https://example.com/1', 'example.com', '2025-02-10', '2025-02', 1))
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Python Tutorial', 'Learn Python programming basics', 
              'https://example.com/2', 'example.com', '2025-02-11', '2025-02', 1))
        
        conn.commit()
        conn.close()
        
        # Label cluster
        service = LabelingService()
        label = service.label_cluster(1)
        
        assert label is not None
        assert label != 'Empty Cluster'
        assert label != 'Unlabeled'
        assert len(label) > 0
    
    def test_label_cluster_empty(self, temp_db, monkeypatch):
        """Test labeling empty cluster."""
        from backend.config import Config
        
        # Create empty cluster
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)", 
                      (1, None, 0, 0.0))
        
        conn.commit()
        conn.close()
        
        # Label cluster
        service = LabelingService()
        label = service.label_cluster(1)
        
        assert label == 'Empty Cluster'
    
    def test_label_all_clusters(self, temp_db, monkeypatch):
        """Test labeling all clusters."""
        from backend.config import Config
        
        # Create clusters and articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Cluster 1: Python articles
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)", 
                      (1, None, 2, 0.0))
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Python Guide', 'Python programming guide', 'https://example.com/1', 'example.com', '2025-02-10', '2025-02', 1))
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Python Tutorial', 'Learn Python', 'https://example.com/2', 'example.com', '2025-02-11', '2025-02', 1))
        
        # Cluster 2: JavaScript articles
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)", 
                      (2, None, 1, 0.0))
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('JavaScript Basics', 'JavaScript programming basics', 'https://example.com/3', 'example.com', '2025-02-12', '2025-02', 2))
        
        conn.commit()
        conn.close()
        
        # Label all clusters
        service = LabelingService()
        stats = service.label_all_clusters(force_recompute=False)
        
        # Verify stats
        assert stats['status'] == 'completed'
        assert stats['clusters_labeled'] >= 2
        
        # Verify labels in database
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, label FROM clusters WHERE id IN (1, 2)")
        clusters = cursor.fetchall()
        
        for cluster in clusters:
            assert cluster['label'] is not None
            assert cluster['label'] != ''
        
        conn.close()
    
    def test_label_all_clusters_idempotent(self, temp_db, monkeypatch):
        """Test that labeling is idempotent."""
        from backend.config import Config
        
        # Create cluster with label
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)", 
                      (1, 'Existing Label', 1, 0.0))
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Test Article', 'Test summary', 'https://example.com/1', 'example.com', '2025-02-10', '2025-02', 1))
        
        conn.commit()
        conn.close()
        
        # Label clusters (should skip already labeled)
        service = LabelingService()
        stats = service.label_all_clusters(force_recompute=False)
        
        # Should skip if label already exists
        assert stats['status'] == 'skipped'
        
        # Verify label unchanged
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT label FROM clusters WHERE id = 1")
        label = cursor.fetchone()['label']
        assert label == 'Existing Label'
        conn.close()

