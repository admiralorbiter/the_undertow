"""
Pytest fixtures for testing.
Provides isolated test database and sample data.
"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from backend.db import init_db, get_db


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary SQLite database for testing."""
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Temporarily override the DATABASE_PATH using monkeypatch
    from backend.config import Config
    original_path = Config.DATABASE_PATH
    monkeypatch.setattr(Config, 'DATABASE_PATH', db_path)
    
    try:
        # Initialize the database
        init_db()
        
        yield db_path
    finally:
        # Ensure all connections are closed before cleanup
        # Close any open connections
        from backend.db import get_db
        try:
            conn = get_db()
            conn.close()
        except Exception:
            pass
        
        # Clean up
        monkeypatch.setattr(Config, 'DATABASE_PATH', original_path)
        
        # On Windows, we may need to wait a bit for file handles to close
        import time
        import sys
        if sys.platform == 'win32':
            time.sleep(0.1)
        
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                # On Windows, sometimes files are still locked
                # Try again after a short delay
                time.sleep(0.2)
                try:
                    os.unlink(db_path)
                except PermissionError:
                    pass  # Give up, OS will clean up temp files


@pytest.fixture
def db_connection(temp_db, monkeypatch):
    """Get a database connection to the test database."""
    from backend.config import Config
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def sample_article_data():
    """Sample article data for testing."""
    return {
        'title': 'Test Article Title',
        'summary': 'This is a test article summary for testing purposes.',
        'url': 'https://example.com/test-article',
        'outlet': 'example.com',
        'date': '2025-02-10',
        'date_bin': '2025-02'
    }


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing ingestion."""
    return """Title,Date,URL,Summary
Test Article 1,2/10/25,https://www.example.com/article1,Summary of article 1
Test Article 2,02/11/2025,https://example.com/article2,Summary of article 2
Test Article 3,2025-02-12,https://test.com/article3,Summary of article 3"""

