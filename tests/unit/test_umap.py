"""
Tests for UMAP projection service.
"""
import pytest
import numpy as np
import sqlite3

# Skip tests if dependencies aren't installed
try:
    import umap
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

if HAS_DEPENDENCIES:
    from backend.services.umap_projection import UMAPService
    from backend.services.embeddings import EmbeddingService
    from backend.config import Config

pytestmark = pytest.mark.skipif(not HAS_DEPENDENCIES, reason="ML dependencies not installed")


class TestUMAPService:
    """Test UMAP projection functionality."""
    
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
        umap_service = UMAPService()
        embeddings, article_ids = umap_service._load_embeddings()
        
        assert len(embeddings) >= 1
        assert len(article_ids) >= 1
        assert embeddings.shape[1] == Config.EMBEDDING_DIM
        assert embeddings.dtype == np.float32
        assert article_id in article_ids
    
    def test_project_to_2d(self):
        """Test UMAP 2D projection."""
        service = UMAPService()
        
        # Create synthetic embeddings (normalized)
        n_samples = 20
        n_features = Config.EMBEDDING_DIM
        embeddings = np.random.randn(n_samples, n_features).astype(np.float32)
        
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        
        # Project to 2D
        coords_2d = service.project_to_2d(embeddings)
        
        assert coords_2d.shape == (n_samples, 2)
        assert coords_2d.dtype in [np.float32, np.float64]
        assert not np.any(np.isnan(coords_2d))
        assert not np.any(np.isinf(coords_2d))
    
    def test_compute_umap_projection(self, temp_db, monkeypatch):
        """Test computing UMAP projection end-to-end."""
        from backend.config import Config
        
        # Create articles and generate embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        articles = [
            ('Python Programming', 'Learn Python', 'https://example.com/python', 'example.com', '2025-02-10', '2025-02'),
            ('Python Tutorial', 'Python basics', 'https://example.com/tutorial', 'example.com', '2025-02-11', '2025-02'),
            ('JavaScript Guide', 'JavaScript intro', 'https://example.com/js', 'example.com', '2025-02-12', '2025-02'),
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
        
        # Compute UMAP projection
        umap_service = UMAPService()
        stats = umap_service.compute_umap_projection(force_recompute=False)
        
        # Verify results
        assert stats['status'] == 'completed'
        assert stats['points_projected'] >= 3
        
        # Verify coordinates in database
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, umap_x, umap_y FROM articles
            WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
        """)
        
        coords_rows = cursor.fetchall()
        assert len(coords_rows) >= 3
        
        for row in coords_rows:
            assert row['umap_x'] is not None
            assert row['umap_y'] is not None
            assert isinstance(row['umap_x'], (int, float))
            assert isinstance(row['umap_y'], (int, float))
        
        conn.close()
    
    def test_update_article_coordinates(self, temp_db, monkeypatch):
        """Test updating article coordinates."""
        from backend.config import Config
        
        # Create article
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test', 'Summary', 'https://example.com/test', 'example.com', '2025-02-10', '2025-02'))
        article_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create fake 2D coordinates
        coords_2d = np.array([[1.5, -2.3]], dtype=np.float32)
        article_ids = [article_id]
        
        # Update coordinates
        umap_service = UMAPService()
        umap_service.update_article_coordinates(article_ids, coords_2d)
        
        # Verify update
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT umap_x, umap_y FROM articles WHERE id = ?
        """, (article_id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert abs(float(row['umap_x']) - 1.5) < 0.001
        assert abs(float(row['umap_y']) - (-2.3)) < 0.001
        
        conn.close()
    
    def test_compute_umap_reproducibility(self, temp_db, monkeypatch):
        """Test that UMAP projection is reproducible with fixed seed."""
        from backend.config import Config
        
        # Create articles and embeddings
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        for i in range(5):
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f'Article {i}', f'Summary {i}', f'https://example.com/{i}', 'example.com', '2025-02-10', '2025-02'))
        
        conn.commit()
        conn.close()
        
        # Generate embeddings
        embedding_service = EmbeddingService()
        embedding_service.generate_embeddings(force_recompute=False)
        
        # Run UMAP twice (should produce same results due to random_state)
        umap_service1 = UMAPService()
        stats1 = umap_service1.compute_umap_projection(force_recompute=False)
        
        # Get first run coordinates
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, umap_x, umap_y FROM articles WHERE umap_x IS NOT NULL ORDER BY id")
        coords1 = {row['id']: (row['umap_x'], row['umap_y']) for row in cursor.fetchall()}
        conn.close()
        
        # Run again with force_recompute
        umap_service2 = UMAPService()
        stats2 = umap_service2.compute_umap_projection(force_recompute=True)
        
        # Get second run coordinates
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, umap_x, umap_y FROM articles WHERE umap_x IS NOT NULL ORDER BY id")
        coords2 = {row['id']: (row['umap_x'], row['umap_y']) for row in cursor.fetchall()}
        conn.close()
        
        # Coordinates should be very close (within numerical precision)
        for article_id in coords1:
            x1, y1 = coords1[article_id]
            x2, y2 = coords2[article_id]
            assert abs(x1 - x2) < 0.001, f"X coordinate differs for article {article_id}"
            assert abs(y1 - y2) < 0.001, f"Y coordinate differs for article {article_id}"
    
    def test_compute_umap_idempotent(self, temp_db, monkeypatch):
        """Test that UMAP computation is idempotent."""
        from backend.config import Config
        
        # Create article and embeddings
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
        
        umap_service = UMAPService()
        
        # First run
        stats1 = umap_service.compute_umap_projection(force_recompute=False)
        
        # Second run (should skip)
        stats2 = umap_service.compute_umap_projection(force_recompute=False)
        
        assert stats2['status'] == 'skipped'
        assert stats1['points_projected'] == stats2['points_projected']

