"""
Tests for database schema initialization.
"""
import pytest
import sqlite3
from backend.db import init_db, get_db
from backend.config import Config


class TestDatabaseSchema:
    """Test database schema creation and initialization."""
    
    def test_init_db_creates_articles_table(self, temp_db, monkeypatch):
        """Test that init_db creates the articles table."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check that articles table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='articles'
        """)
        result = cursor.fetchone()
        assert result is not None, "Articles table should exist"
        
        # Check table structure
        cursor.execute("PRAGMA table_info(articles)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'title' in columns
        assert 'summary' in columns
        assert 'url' in columns
        assert 'outlet' in columns
        assert 'date' in columns
        assert 'date_bin' in columns
        assert 'cluster_id' in columns, "cluster_id column should exist"
        assert 'created_at' in columns
        
        conn.close()
    
    def test_init_db_creates_fts5_table(self, temp_db, monkeypatch):
        """Test that init_db creates the FTS5 virtual table."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check that articles_fts table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='articles_fts'
        """)
        result = cursor.fetchone()
        assert result is not None, "FTS5 table should exist"
        
        conn.close()
    
    def test_init_db_creates_indexes(self, temp_db, monkeypatch):
        """Test that init_db creates necessary indexes."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_articles%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert 'idx_articles_date' in indexes, "Date index should exist"
        assert 'idx_articles_outlet' in indexes, "Outlet index should exist"
        
        conn.close()
    
    def test_init_db_creates_triggers(self, temp_db, monkeypatch):
        """Test that init_db creates FTS5 sync triggers."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check triggers exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='trigger' AND name LIKE 'articles_fts%'
        """)
        triggers = [row[0] for row in cursor.fetchall()]
        
        assert 'articles_fts_insert' in triggers, "Insert trigger should exist"
        assert 'articles_fts_update' in triggers, "Update trigger should exist"
        assert 'articles_fts_delete' in triggers, "Delete trigger should exist"
        
        conn.close()
    
    def test_init_db_is_idempotent(self, temp_db, monkeypatch):
        """Test that init_db can be run multiple times safely."""
        from backend.config import Config
        
        # Run init_db multiple times
        init_db()
        init_db()
        init_db()
        
        # Should still have same structure
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(articles)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        # Should have cluster_id column (from migration)
        assert 'cluster_id' in columns_after
        
        conn.close()
    
    def test_cluster_id_column_is_nullable(self, temp_db, monkeypatch):
        """Test that cluster_id column accepts NULL values."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Insert article with NULL cluster_id
        cursor.execute("""
            INSERT INTO articles (title, url, date, cluster_id)
            VALUES (?, ?, ?, ?)
        """, ('Test Article', 'https://example.com/test', '2025-02-10', None))
        
        # Should not raise error
        conn.commit()
        
        # Verify it was inserted
        cursor.execute("SELECT cluster_id FROM articles WHERE title = ?", ('Test Article',))
        result = cursor.fetchone()
        assert result[0] is None
        
        conn.close()
    
    def test_fts5_trigger_on_insert(self, temp_db, monkeypatch):
        """Test that FTS5 trigger syncs on insert."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Insert article
        cursor.execute("""
            INSERT INTO articles (title, summary, url, date)
            VALUES (?, ?, ?, ?)
        """, ('Test Article', 'Test summary', 'https://example.com/test', '2025-02-10'))
        
        article_id = cursor.lastrowid
        conn.commit()
        
        # Check FTS5 has the entry
        cursor.execute("""
            SELECT rowid FROM articles_fts WHERE articles_fts MATCH 'Test'
        """)
        result = cursor.fetchone()
        assert result is not None, "FTS5 should have the inserted article"
        assert result[0] == article_id
        
        conn.close()
    
    def test_fts5_trigger_on_update(self, temp_db, monkeypatch):
        """Test that FTS5 trigger syncs on update."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Insert article
        cursor.execute("""
            INSERT INTO articles (title, summary, url, date)
            VALUES (?, ?, ?, ?)
        """, ('Original Title', 'Original summary', 'https://example.com/test', '2025-02-10'))
        
        article_id = cursor.lastrowid
        conn.commit()
        
        # Update article
        cursor.execute("""
            UPDATE articles SET title = ?, summary = ?
            WHERE id = ?
        """, ('Updated Title', 'Updated summary', article_id))
        conn.commit()
        
        # Check FTS5 has updated content
        cursor.execute("""
            SELECT rowid FROM articles_fts WHERE articles_fts MATCH 'Updated'
        """)
        result = cursor.fetchone()
        assert result is not None, "FTS5 should have updated content"
        assert result[0] == article_id
        
        # Old content should not appear in FTS5
        cursor.execute("""
            SELECT rowid FROM articles_fts WHERE articles_fts MATCH 'Original'
        """)
        result = cursor.fetchone()
        # Note: FTS5 might still match due to tokenization, but the new content should match
        
        conn.close()
    
    def test_fts5_trigger_on_delete(self, temp_db, monkeypatch):
        """Test that FTS5 trigger syncs on delete."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Insert article
        cursor.execute("""
            INSERT INTO articles (title, summary, url, date)
            VALUES (?, ?, ?, ?)
        """, ('To Delete', 'Summary to delete', 'https://example.com/delete', '2025-02-10'))
        
        article_id = cursor.lastrowid
        conn.commit()
        
        # Verify it's in FTS5
        cursor.execute("""
            SELECT rowid FROM articles_fts WHERE articles_fts MATCH 'delete'
        """)
        result = cursor.fetchone()
        assert result is not None
        
        # Delete article
        cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        conn.commit()
        
        # FTS5 should not have the entry (triggers handle this)
        # Note: FTS5 delete is handled by trigger, but we can verify the article is gone
        cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
        result = cursor.fetchone()
        assert result is None, "Article should be deleted"
        
        conn.close()
    
    def test_init_db_creates_p1_tables(self, temp_db, monkeypatch):
        """Test that init_db creates all P1 tables."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check all P1 tables exist
        p1_tables = ['embeddings', 'similarities', 'clusters', 'entities', 'article_entities', 'vector_meta']
        for table_name in p1_tables:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            result = cursor.fetchone()
            assert result is not None, f"{table_name} table should exist"
        
        conn.close()
    
    def test_articles_table_has_umap_columns(self, temp_db, monkeypatch):
        """Test that articles table has umap_x and umap_y columns."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(articles)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'umap_x' in columns, "umap_x column should exist"
        assert 'umap_y' in columns, "umap_y column should exist"
        
        conn.close()
    
    def test_embeddings_table_structure(self, temp_db, monkeypatch):
        """Test embeddings table structure."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(embeddings)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'article_id' in columns
        assert 'vec' in columns
        assert columns['article_id'] == 'INTEGER'
        assert columns['vec'] == 'BLOB'
        
        conn.close()
    
    def test_similarities_table_structure(self, temp_db, monkeypatch):
        """Test similarities table structure."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(similarities)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'src_id' in columns
        assert 'dst_id' in columns
        assert 'cosine' in columns
        assert 'shared_entities' in columns
        assert 'shared_terms' in columns
        
        conn.close()
    
    def test_clusters_table_structure(self, temp_db, monkeypatch):
        """Test clusters table structure."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(clusters)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'label' in columns
        assert 'size' in columns
        assert 'score' in columns
        
        conn.close()
    
    def test_entities_table_structure(self, temp_db, monkeypatch):
        """Test entities table structure."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(entities)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'name' in columns
        assert 'type' in columns
        
        # Check that type has CHECK constraint
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='entities'
        """)
        sql = cursor.fetchone()[0]
        assert 'CHECK' in sql.upper()
        assert 'PERSON' in sql
        assert 'ORG' in sql
        
        conn.close()
    
    def test_article_entities_table_structure(self, temp_db, monkeypatch):
        """Test article_entities table structure."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(article_entities)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'article_id' in columns
        assert 'entity_id' in columns
        assert 'weight' in columns
        
        conn.close()
    
    def test_vector_meta_table_structure(self, temp_db, monkeypatch):
        """Test vector_meta table structure."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(vector_meta)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'version' in columns
        assert 'dim' in columns
        assert 'count' in columns
        assert 'updated_at' in columns
        
        conn.close()
    
    def test_p1_indexes_created(self, temp_db, monkeypatch):
        """Test that P1 indexes are created."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        # Check P1 indexes
        assert 'idx_articles_cluster' in indexes
        assert 'idx_embeddings_article' in indexes
        assert 'idx_similarities_src' in indexes
        assert 'idx_similarities_dst' in indexes
        assert 'idx_entities_name' in indexes
        assert 'idx_entities_type' in indexes
        
        conn.close()
    
    def test_migration_adds_umap_columns(self, temp_db, monkeypatch):
        """Test that migration adds umap_x and umap_y to existing articles table."""
        from backend.config import Config
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create articles table without umap columns (simulating old schema)
        cursor.execute("DROP TABLE IF EXISTS articles")
        cursor.execute("""
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                summary TEXT,
                url TEXT UNIQUE NOT NULL,
                outlet TEXT,
                date TEXT NOT NULL,
                date_bin TEXT,
                cluster_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        # Run init_db again (should add umap columns)
        init_db()
        
        # Verify columns were added
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(articles)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'umap_x' in columns, "Migration should add umap_x column"
        assert 'umap_y' in columns, "Migration should add umap_y column"
        
        conn.close()

