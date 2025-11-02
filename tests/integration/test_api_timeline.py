"""
Integration tests for timeline API endpoint.
"""
import pytest
from app import create_app
import json


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestTimelineAPI:
    """Test timeline API endpoints."""
    
    def test_get_timeline_empty(self, client):
        """Test timeline endpoint with no articles."""
        response = client.get('/api/timeline')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'bins' in data
        assert isinstance(data['bins'], list)
    
    def test_get_timeline_with_data(self, client, temp_db, monkeypatch):
        """Test timeline endpoint with articles."""
        from backend.config import Config
        import sqlite3
        
        # Insert test articles with dates
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        articles = [
            ('Article 1', 'Summary 1', 'https://example.com/1', 'example.com', '2025-02-10', '2025-02'),
            ('Article 2', 'Summary 2', 'https://example.com/2', 'example.com', '2025-02-11', '2025-02'),
            ('Article 3', 'Summary 3', 'https://example.com/3', 'example.com', '2025-03-01', '2025-03'),
        ]
        
        for title, summary, url, outlet, date, date_bin in articles:
            cursor.execute("""
                INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, summary, url, outlet, date, date_bin))
        
        conn.commit()
        conn.close()
        
        # Get timeline
        response = client.get('/api/timeline')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'bins' in data
        assert len(data['bins']) > 0
        
        # Verify bin structure
        for bin_data in data['bins']:
            assert 'date' in bin_data
            assert 'count' in bin_data
            assert 'by_cluster' in bin_data
            assert isinstance(bin_data['count'], int)
            assert isinstance(bin_data['by_cluster'], dict)
    
    def test_get_timeline_with_cluster_filter(self, client, temp_db, monkeypatch):
        """Test timeline endpoint with cluster filter."""
        from backend.config import Config
        import sqlite3
        
        # Create cluster and articles
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO clusters (id, label, size, score) VALUES (?, ?, ?, ?)",
                      (1, 'Test Cluster', 2, 0.0))
        
        cursor.execute("""
            INSERT INTO articles (title, summary, url, outlet, date, date_bin, cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Article 1', 'Summary', 'https://example.com/1', 'example.com', '2025-02-10', '2025-02', 1))
        
        conn.commit()
        conn.close()
        
        # Get timeline filtered by cluster
        response = client.get('/api/timeline?cluster_id=1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'bins' in data

