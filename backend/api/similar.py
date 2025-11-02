"""
Similar articles API endpoints.
Provides similarity information and similar article recommendations.
"""
from flask import Blueprint, jsonify, request
from backend.db import get_db

similar_bp = Blueprint('similar', __name__)


@similar_bp.route('/similar/<int:article_id>', methods=['GET'])
def get_similar(article_id):
    """
    GET /api/similar/:id
    
    Returns top-k similar articles to the given article.
    
    Query parameters:
    - k: Number of results (default: 10, max: 50)
    
    Response:
    {
        "items": [
            {
                "id": 456,
                "title": "Related Article",
                "cosine": 0.87,
                "why": {
                    "shared_entities": ["entity1", "entity2"],
                    "shared_terms": ["term1", "term2"]
                }
            },
            ...
        ],
        "article": {
            "id": 123,
            "title": "Source Article"
        }
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    k = int(request.args.get('k', 10))
    k = max(1, min(k, 50))
    
    try:
        # Verify article exists
        cursor.execute("""
            SELECT id, title FROM articles WHERE id = ?
        """, (article_id,))
        article_row = cursor.fetchone()
        
        if not article_row:
            return jsonify({
                'ok': False,
                'error': {
                    'code': 'ARTICLE_NOT_FOUND',
                    'message': f'Article {article_id} not found'
                }
            }), 404
        
        article = {
            'id': article_row['id'],
            'title': article_row['title']
        }
        
        # Get source article date and outlet for comparison
        cursor.execute("SELECT date, outlet FROM articles WHERE id = ?", (article_id,))
        source_row = cursor.fetchone()
        source_date = source_row['date'] if source_row else None
        source_outlet = source_row['outlet'] if source_row else None
        
        # Get similar articles from similarities table
        cursor.execute("""
            SELECT s.dst_id as id, s.cosine, s.shared_entities, s.shared_terms,
                   a.title, a.summary, a.url, a.outlet, a.date
            FROM similarities s
            JOIN articles a ON s.dst_id = a.id
            WHERE s.src_id = ?
            ORDER BY s.cosine DESC
            LIMIT ?
        """, (article_id, k))
        
        items = []
        for row in cursor.fetchall():
            # Parse JSON fields if they exist
            shared_entities = []
            shared_terms = []
            
            try:
                import json
                if row['shared_entities']:
                    shared_entities = json.loads(row['shared_entities'])
                if row['shared_terms']:
                    shared_terms = json.loads(row['shared_terms'])
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Compute date proximity
            date_proximity = None
            if source_date and row['date']:
                try:
                    from datetime import datetime
                    source_dt = datetime.fromisoformat(source_date.split('T')[0])
                    similar_dt = datetime.fromisoformat(row['date'].split('T')[0])
                    delta = abs((similar_dt - source_dt).days)
                    date_proximity = delta
                except (ValueError, AttributeError):
                    pass
            
            # Compute outlet overlap
            outlet_overlap = source_outlet and row['outlet'] and source_outlet == row['outlet']
            
            items.append({
                'id': row['id'],
                'title': row['title'],
                'summary': row['summary'],
                'url': row['url'],
                'outlet': row['outlet'],
                'date': row['date'],
                'cosine': float(row['cosine']) if row['cosine'] is not None else None,
                'why': {
                    'shared_entities': shared_entities,
                    'shared_terms': shared_terms,
                    'date_proximity_days': date_proximity,
                    'same_outlet': outlet_overlap
                }
            })
        
        return jsonify({
            'items': items,
            'article': article
        })
    finally:
        conn.close()

