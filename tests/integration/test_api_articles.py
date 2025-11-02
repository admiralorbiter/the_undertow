"""
Integration tests for API endpoints.
"""
import pytest
import json
import tempfile
from pathlib import Path
from app import create_app
from backend.services.ingest import ingest_csv


@pytest.fixture
def app(temp_db, monkeypatch):
    """Create Flask app with test database."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_articles_data(temp_db, monkeypatch, client):
    """Insert sample articles for testing."""
    from backend.config import Config
    
    # Create a temporary CSV file
    csv_content = """Title,Date,URL,Summary
Test Article 1,2/10/25,https://www.example.com/article1,Summary of article 1 about Python
Test Article 2,02/11/2025,https://example.com/article2,Summary of article 2 about JavaScript
Test Article 3,2025-02-12,https://other.com/article3,Summary of article 3 about web development"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        csv_path = Path(f.name)
    
    # Ingest articles
    ingest_csv(csv_path)
    
    # Clean up
    Path(csv_path).unlink()


class TestGetArticles:
    """Test GET /api/articles endpoint."""
    
    def test_get_articles_empty_database(self, client):
        """Test getting articles from empty database."""
        response = client.get('/api/articles')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'items' in data
        assert 'total' in data
        assert data['total'] == 0
        assert len(data['items']) == 0
    
    def test_get_articles_with_data(self, client, sample_articles_data):
        """Test getting articles returns data."""
        response = client.get('/api/articles')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'items' in data
        assert 'total' in data
        assert data['total'] >= 3
        assert len(data['items']) >= 3
    
    def test_get_articles_full_text_search(self, client, sample_articles_data):
        """Test full-text search via q parameter."""
        response = client.get('/api/articles?q=Python')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['total'] >= 1
        # At least one article should contain "Python" in title or summary
        items_text = [item['title'] + ' ' + (item.get('summary', '') or '') for item in data['items']]
        assert any('Python' in text or 'python' in text.lower() for text in items_text)
    
    def test_get_articles_date_filter_from(self, client, sample_articles_data):
        """Test date filtering with from parameter."""
        response = client.get('/api/articles?from=2025-02-11')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # All articles should be >= 2025-02-11
        for item in data['items']:
            assert item['date'] >= '2025-02-11'
    
    def test_get_articles_date_filter_to(self, client, sample_articles_data):
        """Test date filtering with to parameter."""
        response = client.get('/api/articles?to=2025-02-11')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # All articles should be <= 2025-02-11
        for item in data['items']:
            assert item['date'] <= '2025-02-11'
    
    def test_get_articles_date_filter_range(self, client, sample_articles_data):
        """Test date filtering with both from and to."""
        response = client.get('/api/articles?from=2025-02-10&to=2025-02-11')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # All articles should be in date range
        for item in data['items']:
            assert '2025-02-10' <= item['date'] <= '2025-02-11'
    
    def test_get_articles_outlet_filter(self, client, sample_articles_data):
        """Test outlet filtering."""
        response = client.get('/api/articles?outlet=example.com')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # All articles should be from example.com
        for item in data['items']:
            assert item['outlet'] == 'example.com'
    
    def test_get_articles_combined_filters(self, client, sample_articles_data):
        """Test combined filters (search, date, outlet)."""
        response = client.get('/api/articles?q=article&from=2025-02-10&to=2025-02-11&outlet=example.com')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Verify all items match filters
        for item in data['items']:
            assert item['outlet'] == 'example.com'
            assert '2025-02-10' <= item['date'] <= '2025-02-11'
    
    def test_get_articles_pagination_limit(self, client, sample_articles_data):
        """Test pagination with limit parameter."""
        response = client.get('/api/articles?limit=2')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['items']) <= 2
    
    def test_get_articles_pagination_offset(self, client, sample_articles_data):
        """Test pagination with offset parameter."""
        response1 = client.get('/api/articles?limit=2&offset=0')
        response2 = client.get('/api/articles?limit=2&offset=2')
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)
        
        # Results should be different (if we have more than 2 articles)
        if len(data1['items']) == 2 and len(data2['items']) > 0:
            ids1 = {item['id'] for item in data1['items']}
            ids2 = {item['id'] for item in data2['items']}
            assert ids1.isdisjoint(ids2)
    
    def test_get_articles_response_format(self, client, sample_articles_data):
        """Test response format matches spec."""
        response = client.get('/api/articles')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'items' in data
        assert 'total' in data
        assert isinstance(data['items'], list)
        assert isinstance(data['total'], int)
        
        # Check item structure
        if data['items']:
            item = data['items'][0]
            assert 'id' in item
            assert 'title' in item
            assert 'date' in item
            assert 'url' in item
            assert 'outlet' in item
    
    def test_get_articles_limit_clamping(self, client, sample_articles_data):
        """Test that limit is clamped to reasonable values."""
        # Test negative limit
        response = client.get('/api/articles?limit=-5')
        assert response.status_code == 200
        
        # Test very large limit
        response = client.get('/api/articles?limit=10000')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['items']) <= 1000  # Max limit should be 1000


class TestIngestCsv:
    """Test POST /api/ingest/csv endpoint."""
    
    def test_ingest_csv_success(self, client, temp_db, monkeypatch):
        """Test successful CSV ingestion."""
        from backend.config import Config
        
        # Create a temporary CSV file
        csv_content = """Title,Date,URL,Summary
New Article 1,2/15/25,https://example.com/new1,Summary 1
New Article 2,2/16/25,https://example.com/new2,Summary 2"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = Path(f.name)
        
        csv_filename = csv_path.name
        
        try:
            # Place CSV in data directory for API to find
            data_dir = Path(Config.DATA_DIR)
            data_dir.mkdir(exist_ok=True)
            target_path = data_dir / csv_filename
            csv_path.rename(target_path)
            
            response = client.post(f'/api/ingest/csv?path={csv_filename}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['ok'] is True
            assert 'stats' in data
            assert 'inserted' in data['stats']
            assert data['stats']['inserted'] == 2
            
            # Clean up
            target_path.unlink()
        except Exception as e:
            # Clean up on error
            if target_path.exists():
                target_path.unlink()
            raise
    
    def test_ingest_csv_file_not_found(self, client):
        """Test ingestion with missing file returns 404."""
        response = client.post('/api/ingest/csv?path=nonexistent.csv')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['ok'] is False
        assert 'error' in data
        assert data['error']['code'] == 'FILE_NOT_FOUND'
    
    def test_ingest_csv_error_response_format(self, client):
        """Test error response format matches spec."""
        response = client.post('/api/ingest/csv?path=nonexistent.csv')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'ok' in data
        assert data['ok'] is False
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
    
    def test_ingest_csv_duplicate_handling(self, client, temp_db, monkeypatch):
        """Test that duplicate URLs are handled correctly."""
        from backend.config import Config
        
        csv_content = """Title,Date,URL,Summary
Duplicate Test,2/15/25,https://example.com/dup,Summary"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = Path(f.name)
        
        csv_filename = csv_path.name
        
        try:
            # Place CSV in data directory
            data_dir = Path(Config.DATA_DIR)
            data_dir.mkdir(exist_ok=True)
            target_path = data_dir / csv_filename
            csv_path.rename(target_path)
            
            # Ingest twice
            response1 = client.post(f'/api/ingest/csv?path={csv_filename}')
            response2 = client.post(f'/api/ingest/csv?path={csv_filename}')
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            data1 = json.loads(response1.data)
            data2 = json.loads(response2.data)
            
            assert data1['stats']['inserted'] == 1
            assert data2['stats']['inserted'] == 0
            assert data2['stats']['skipped'] == 1
            
            # Clean up
            target_path.unlink()
        except Exception as e:
            if target_path.exists():
                target_path.unlink()
            raise

