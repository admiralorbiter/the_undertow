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
    
    # Add P1/P2 columns to articles table if they don't exist (migration for existing databases)
    for column in ['cluster_id', 'umap_x', 'umap_y', 'storyline_id']:
        try:
            if column == 'storyline_id':
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {column} INTEGER REFERENCES storylines(id)")
            else:
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {column} REAL")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
    
    # Create embeddings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            article_id INTEGER PRIMARY KEY,
            vec BLOB NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    
    # Create similarities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS similarities (
            src_id INTEGER NOT NULL,
            dst_id INTEGER NOT NULL,
            cosine REAL NOT NULL,
            shared_entities TEXT,
            shared_terms TEXT,
            tier TEXT CHECK(tier IN ('near_duplicate', 'continuation', 'related')),
            PRIMARY KEY (src_id, dst_id),
            FOREIGN KEY (src_id) REFERENCES articles(id) ON DELETE CASCADE,
            FOREIGN KEY (dst_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    
    # Add tier column to similarities if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE similarities ADD COLUMN tier TEXT CHECK(tier IN ('near_duplicate', 'continuation', 'related'))")
    except sqlite3.OperationalError:
        # Column already exists, which is fine
        pass
    
    # Create clusters table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            size INTEGER,
            score REAL
        )
    """)
    
    # Create entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT CHECK(type IN ('PERSON','ORG','GPE','LOC','OTHER')),
            canonical_name TEXT
        )
    """)
    
    # Add canonical_name column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE entities ADD COLUMN canonical_name TEXT")
    except sqlite3.OperationalError:
        # Column already exists, which is fine
        pass
    
    # Create entity_roles table (P2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_roles (
            entity_id INTEGER NOT NULL,
            article_id INTEGER NOT NULL,
            role_type TEXT CHECK(role_type IN ('protagonist', 'antagonist', 'subject', 'adjudicator', 'neutral')) NOT NULL,
            confidence REAL DEFAULT 0.5,
            evidence TEXT,
            PRIMARY KEY (entity_id, article_id),
            FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    
    # Create storylines table (P2.2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storylines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            status TEXT CHECK(status IN ('active', 'dormant', 'concluded')),
            momentum_score REAL DEFAULT 0.0,
            first_date TEXT NOT NULL,
            last_date TEXT NOT NULL,
            article_count INTEGER DEFAULT 0
        )
    """)
    
    # Create storyline_articles table (P2.2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storyline_articles (
            storyline_id INTEGER NOT NULL,
            article_id INTEGER NOT NULL,
            tier TEXT CHECK(tier IN ('tier1', 'tier2', 'tier3')),
            sequence_order INTEGER NOT NULL,
            PRIMARY KEY (storyline_id, article_id),
            FOREIGN KEY (storyline_id) REFERENCES storylines(id) ON DELETE CASCADE,
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    
    # Create alerts table (P3.2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT CHECK(alert_type IN ('topic_surge', 'story_reactivation', 'new_actor', 'divergence')) NOT NULL,
            entity_json TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT CHECK(severity IN ('low', 'medium', 'high')) DEFAULT 'medium',
            acknowledged BOOLEAN DEFAULT 0
        )
    """)
    
    # Create article_entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_entities (
            article_id INTEGER NOT NULL,
            entity_id INTEGER NOT NULL,
            weight REAL,
            count INTEGER DEFAULT 1,
            first_mention_char INTEGER,
            confidence REAL DEFAULT 1.0,
            PRIMARY KEY (article_id, entity_id),
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
            FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
        )
    """)
    
    # Add P2 columns to article_entities if they don't exist (migration)
    for column in ['count', 'first_mention_char', 'confidence']:
        try:
            if column == 'count':
                cursor.execute(f"ALTER TABLE article_entities ADD COLUMN {column} INTEGER DEFAULT 1")
            elif column == 'first_mention_char':
                cursor.execute(f"ALTER TABLE article_entities ADD COLUMN {column} INTEGER")
            elif column == 'confidence':
                cursor.execute(f"ALTER TABLE article_entities ADD COLUMN {column} REAL DEFAULT 1.0")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
    
    # Create vector_meta table for FAISS index metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vector_meta (
            version INTEGER PRIMARY KEY DEFAULT 1,
            dim INTEGER NOT NULL,
            count INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_cluster 
        ON articles(cluster_id)
    """)
    
    # Create indexes for P1 tables
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_article 
        ON embeddings(article_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_similarities_src 
        ON similarities(src_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_similarities_dst 
        ON similarities(dst_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_name 
        ON entities(name)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_type 
        ON entities(type)
    """)
    
    # Create indexes for entity_roles table (P2)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_roles_article 
        ON entity_roles(article_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_roles_entity 
        ON entity_roles(entity_id)
    """)
    
    # Create indexes for storylines tables (P2.2)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_storyline 
        ON articles(storyline_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_storyline_articles_order
        ON storyline_articles(storyline_id, sequence_order)
    """)
    
    # Create indexes for alerts table (P3.2)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_triggered
        ON alerts(triggered_at DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_type
        ON alerts(alert_type)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_severity
        ON alerts(severity)
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

