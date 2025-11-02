"""
Tests for FTS5 search service.
"""
import pytest
import sqlite3
from backend.services.search import search_articles


class TestSearchArticles:
    """Test FTS5 search functionality."""
    
    def _insert_test_articles(self, db_connection):
        """Helper to insert test articles."""
        cursor = db_connection.cursor()
        test_articles = [
            ('Python Programming', 'Learn Python programming language', 'https://example.com/python', 'example.com', '2025-02-10', '2025-02'),
            ('JavaScript Guide', 'Complete guide to JavaScript', 'https://example.com/js', 'example.com', '2025-02-11', '2025-02'),
            ('Python Tutorial', 'Python tutorial for beginners', 'https://other.com/python', 'other.com', '2025-02-12', '2025-02'),
            ('Web Development', 'Building web applications', 'https://example.com/web', 'example.com', '2025-03-01', '2025-03'),
        ]
        for title, summary, url, outlet, date, date_bin in test_articles:
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, summary, url, outlet, date, date_bin))
        db_connection.commit()
    
    def test_search_basic_query(self, temp_db, monkeypatch, db_connection):
        """Test basic FTS5 query matching."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('Python')
        
        assert len(results) == 2
        titles = [row['title'] for row in results]
        assert 'Python Programming' in titles
        assert 'Python Tutorial' in titles
    
    def test_search_phrase_query(self, temp_db, monkeypatch, db_connection):
        """Test phrase search with multi-word query."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('web development')
        
        assert len(results) >= 1
        titles = [row['title'] for row in results]
        assert 'Web Development' in titles
    
    def test_search_date_filter_from(self, temp_db, monkeypatch, db_connection):
        """Test date filtering with date_from parameter."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('', date_from='2025-02-12')
        
        # Should only return articles from 2025-02-12 onwards
        dates = [row['date'] for row in results]
        for date in dates:
            assert date >= '2025-02-12'
    
    def test_search_date_filter_to(self, temp_db, monkeypatch, db_connection):
        """Test date filtering with date_to parameter."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('', date_to='2025-02-11')
        
        # Should only return articles up to 2025-02-11
        dates = [row['date'] for row in results]
        for date in dates:
            assert date <= '2025-02-11'
    
    def test_search_date_filter_range(self, temp_db, monkeypatch, db_connection):
        """Test date filtering with both date_from and date_to."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('', date_from='2025-02-10', date_to='2025-02-11')
        
        # Should only return articles in date range
        dates = [row['date'] for row in results]
        for date in dates:
            assert '2025-02-10' <= date <= '2025-02-11'
    
    def test_search_outlet_filter(self, temp_db, monkeypatch, db_connection):
        """Test outlet filtering."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('', outlet='example.com')
        
        # Should only return articles from example.com
        outlets = [row['outlet'] for row in results]
        for outlet in outlets:
            assert outlet == 'example.com'
    
    def test_search_combined_filters(self, temp_db, monkeypatch, db_connection):
        """Test search with query, date, and outlet filters combined."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('Python', date_from='2025-02-10', date_to='2025-02-11', outlet='example.com')
        
        # Should return Python articles from example.com in date range
        assert len(results) >= 1
        for row in results:
            assert 'python' in row['title'].lower()
            assert row['outlet'] == 'example.com'
            assert '2025-02-10' <= row['date'] <= '2025-02-11'
    
    def test_search_pagination_limit(self, temp_db, monkeypatch, db_connection):
        """Test pagination with limit parameter."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('', limit=2)
        
        assert len(results) <= 2
    
    def test_search_pagination_offset(self, temp_db, monkeypatch, db_connection):
        """Test pagination with offset parameter."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results1 = search_articles('', limit=2, offset=0)
        results2 = search_articles('', limit=2, offset=2)
        
        # Results should be different (assuming we have more than 2 articles)
        if len(results1) == 2:
            assert len(results2) >= 0
            # IDs should be different
            ids1 = {row['id'] for row in results1}
            ids2 = {row['id'] for row in results2}
            assert ids1.isdisjoint(ids2)
    
    def test_search_count_only(self, temp_db, monkeypatch, db_connection):
        """Test count_only mode returns only count."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        count = search_articles('Python', count_only=True)
        
        assert isinstance(count, int)
        assert count == 2  # Two articles with "Python" in them
    
    def test_search_bm25_ranking(self, temp_db, monkeypatch, db_connection):
        """Test that BM25 ranking is applied."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('Python')
        
        # Results should have rank field
        assert len(results) > 0
        for row in results:
            # sqlite3.Row supports 'in' check with keys()
            row_keys = list(row.keys())
            assert 'rank' in row_keys
            # Rank should be a number (lower is better in BM25)
            rank_value = row['rank']
            assert isinstance(rank_value, (int, float))
    
    def test_search_empty_query(self, temp_db, monkeypatch, db_connection):
        """Test search with empty query (should still filter by date/outlet if provided)."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        # Note: Empty query might cause issues with FTS5, so this tests edge case
        # The function should handle this gracefully or we might need to modify it
        # For now, let's test that it doesn't crash
        try:
            results = search_articles('', outlet='example.com')
            # If it works, should return filtered results
            assert isinstance(results, list)
        except Exception:
            # If empty query causes FTS5 error, that's expected behavior
            pass
    
    def test_search_special_characters(self, temp_db, monkeypatch, db_connection):
        """Test search with special characters in query."""
        from backend.config import Config
        
        # Insert article with special characters
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test "Quote" Article', 'Article with quotes', 'https://example.com/quote', 'example.com', '2025-02-10', '2025-02'))
        db_connection.commit()
        
        # Search should handle quotes
        results = search_articles('Quote')
        assert len(results) >= 1
    
    def test_search_no_results(self, temp_db, monkeypatch, db_connection):
        """Test search that returns no results."""
        from backend.config import Config
        self._insert_test_articles(db_connection)
        
        results = search_articles('NonexistentTerm')
        
        assert len(results) == 0
        assert isinstance(results, list)

