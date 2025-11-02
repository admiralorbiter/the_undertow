"""
Tests for clustering service.
"""
import pytest
import numpy as np
import sqlite3

# Skip tests if dependencies aren't installed
try:
    import hdbscan
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

if HAS_DEPENDENCIES:
    from backend.services.clustering import ClusteringService
    from backend.services.embeddings import EmbeddingService
    from backend.config import Config

pytestmark = pytest.mark.skipif(not HAS_DEPENDENCIES, reason="ML dependencies not installed")


class TestClusteringService:
    """Test clustering functionality."""
    
    def test_load_embeddings(self, temp_db, monkeypatch):
        """Test loading embeddings from database."""
        from backend.config import Config
        
        # Create articles and embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test Article', 'Test summary', 'https://example.com/test', 'example.com', '2025-02-10', '2025-02'))
        article_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate embeddings
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        
        # Load embeddings
        clustering_service = ClusteringService()
        embeddings, article_ids = clustering_service._load_embeddings()
        
        assert len(embeddings) >= 1
        assert len(article_ids) >= 1
        assert embeddings.shape[1] == Config.EMBEDDING_DIM
        assert embeddings.dtype == np.float32
        assert article_id in article_ids
    
    def test_cluster_articles_hdbscan(self, temp_db, monkeypatch):
        """Test clustering articles with HDBSCAN."""
        from backend.config import Config
        
        # Create multiple articles and generate embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        articles = [
            ('Python Programming', 'Learn Python programming', 'https://example.com/python', 'example.com', '2025-02-10', '2025-02'),
            ('Python Tutorial', 'Python tutorial for beginners', 'https://example.com/tutorial', 'example.com', '2025-02-11', '2025-02'),
            ('JavaScript Guide', 'JavaScript programming guide', 'https://example.com/js', 'example.com', '2025-02-12', '2025-02'),
            ('JavaScript Basics', 'Learn JavaScript basics', 'https://example.com/js2', 'example.com', '2025-02-13', '2025-02'),
            ('Java Introduction', 'Java programming intro', 'https://example.com/java', 'example.com', '2025-02-14', '2025-02'),
            ('Java Fundamentals', 'Java fundamentals guide', 'https://example.com/java2', 'example.com', '2025-02-15', '2025-02'),
            ('C++ Programming', 'C++ programming tutorial', 'https://example.com/cpp', 'example.com', '2025-02-16', '2025-02'),
            ('C++ Advanced', 'Advanced C++ concepts', 'https://example.com/cpp2', 'example.com', '2025-02-17', '2025-02'),
        ]
        
        for title, summary, url, outlet, date, date_bin in articles:
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, summary, url, outlet, date, date_bin))
        
        conn.commit()
        conn.close()
        
        # Generate embeddings
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        
        # Cluster articles
        clustering_service = ClusteringService()
        stats = clustering_service.cluster_articles(force_recompute=False)
        
        # Verify clustering results
        assert stats['status'] == 'completed'
        assert stats['clusters_created'] >= 0
        assert stats['articles_clustered'] >= 0
        assert stats['noise'] >= 0
        assert stats['method'] in ['hdbscan', 'kmeans']
        
        # Verify clusters in database
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM clusters")
        clusters_count = cursor.fetchone()[0]
        assert clusters_count == stats['clusters_created']
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE cluster_id IS NOT NULL")
        clustered_count = cursor.fetchone()[0]
        assert clustered_count == stats['articles_clustered']
        
        conn.close()
    
    def test_update_article_clusters(self, temp_db, monkeypatch):
        """Test updating article cluster_ids."""
        from backend.config import Config
        
        # Create articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        article_ids = []
        for i in range(5):
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f'Article {i}', f'Summary {i}', f'https://example.com/{i}', 'example.com', '2025-02-10', '2025-02'))
            article_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        
        # Create fake embeddings and test cluster update
        embedding_service = EmbeddingService()
        
        # Generate real embeddings
        embedding_service.generate_embeddings(force_recompute=False)
        
        # Cluster
        clustering_service = ClusteringService()
        stats = clustering_service.cluster_articles(force_recompute=False)
        
        # Verify cluster_ids were updated
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, cluster_id FROM articles WHERE id IN ({})
        """.format(','.join('?' * len(article_ids))), article_ids)
        
        for row in cursor.fetchall():
            # cluster_id can be NULL (noise) or an integer
            assert row['cluster_id'] is None or isinstance(row['cluster_id'], int)
        
        conn.close()
    
    def test_update_clusters_table(self, temp_db, monkeypatch):
        """Test updating clusters table."""
        from backend.config import Config
        
        # Create articles and embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        for i in range(10):
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f'Article {i}', f'Summary {i}', f'https://example.com/{i}', 'example.com', '2025-02-10', '2025-02'))
        
        conn.commit()
        conn.close()
        
        # Generate embeddings and cluster
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        
        clustering_service = ClusteringService()
        stats = clustering_service.cluster_articles(force_recompute=False)
        
        # Verify clusters table
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, label, size, score FROM clusters")
        clusters = cursor.fetchall()
        
        assert len(clusters) == stats['clusters_created']
        
        for cluster in clusters:
            assert isinstance(cluster['id'], int)
            assert cluster['size'] > 0
            assert cluster['score'] is not None
        
        conn.close()
    
    def test_cluster_articles_idempotent(self, temp_db, monkeypatch):
        """Test that clustering is idempotent (doesn't recompute if exists)."""
        from backend.config import Config
        
        # Create articles and cluster once
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test', 'Summary', 'https://example.com/test', 'example.com', '2025-02-10', '2025-02'))
        conn.commit()
        conn.close()
        
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        
        clustering_service = ClusteringService()
        
        # First run
        stats1 = clustering_service.cluster_articles(force_recompute=False)
        
        # Second run (should skip)
        stats2 = clustering_service.cluster_articles(force_recompute=False)
        
        assert stats2['status'] == 'skipped'
        assert stats2['method'] == 'existing'
        assert stats1['clusters_created'] == stats2['clusters_created']

