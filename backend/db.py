"""
Database connection and schema initialization.
Uses SQLite with FTS5 for full-text search.
"""
import sqlite3
from pathlib import Path
from backend.config import Config


def get_db():
    """Get a database connection."""
    Config.ensure_directories()
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_db():
    """Initialize the database schema (idempotent)."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create articles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
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
    
    # Add cluster_id column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN cluster_id INTEGER")
    except sqlite3.OperationalError:
        # Column already exists, which is fine
        pass
    
    # Create full-text search virtual table (FTS5)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            summary,
            content='articles',
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_date 
        ON articles(date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_outlet 
        ON articles(outlet)
    """)
    
    # Create trigger to keep FTS5 in sync with articles table
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_fts_insert AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, title, summary) 
            VALUES (new.id, new.title, new.summary);
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_fts_delete AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary) 
            VALUES('delete', old.id, old.title, old.summary);
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_fts_update AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary) 
            VALUES('delete', old.id, old.title, old.summary);
            INSERT INTO articles_fts(rowid, title, summary) 
            VALUES (new.id, new.title, new.summary);
        END
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {Config.DATABASE_PATH}")

