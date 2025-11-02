"""
Article API endpoints.
Provides list, search, and filtering capabilities.
"""
from flask import Blueprint, request, jsonify
from backend.db import get_db
from backend.services.search import search_articles
from backend.services.ingest import ingest_csv
from pathlib import Path
from backend.config import Config


articles_bp = Blueprint('articles', __name__)


@articles_bp.route('/articles', methods=['GET'])
def get_articles():
    """
    GET /api/articles
    
    Query parameters:
    - q: Full-text search query
    - from: Start date (YYYY-MM-DD)
    - to: End date (YYYY-MM-DD)
    - outlet: Filter by outlet (domain name)
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)
    
    Returns:
    {
        "items": [{"id", "title", "date", "url", "outlet", "summary"}],
        "total": int
    }
    """
    # Parse query parameters
    query = request.args.get('q', '').strip()
    date_from = request.args.get('from', '').strip()
    date_to = request.args.get('to', '').strip()
    outlet = request.args.get('outlet', '').strip()
    cluster_id = request.args.get('cluster_id', type=int)
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # Clamp limit to reasonable range
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)
    
    # Build query
    conn = get_db()
    cursor = conn.cursor()
    
    # Use FTS5 if query provided, otherwise regular SELECT
    if query:
        results = search_articles(query, date_from, date_to, outlet, cluster_id, limit, offset)
        total = search_articles(query, date_from, date_to, outlet, cluster_id, limit=10000, offset=0, count_only=True)
    else:
        # Build WHERE clause
        conditions = []
        params = []
        
        if date_from:
            conditions.append("date >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("date <= ?")
            params.append(date_to)
        
        if outlet:
            conditions.append("outlet = ?")
            params.append(outlet)
        
        if cluster_id is not None:
            conditions.append("cluster_id = ?")
            params.append(cluster_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM articles {where_clause}", params)
        total = cursor.fetchone()[0]
        
        # Get articles
        params.extend([limit, offset])
        cursor.execute(f"""
            SELECT id, title, summary, url, outlet, date, date_bin
            FROM articles
            {where_clause}
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
        """, params)
        
        results = cursor.fetchall()
    
    # Format results
    items = []
    for row in results:
        if isinstance(row, dict):
            item = row
        else:
            item = {
                'id': row['id'],
                'title': row['title'],
                'summary': row['summary'],
                'url': row['url'],
                'outlet': row['outlet'],
                'date': row['date'],
                'date_bin': row['date_bin']
            }
        items.append(item)
    
    conn.close()
    
    return jsonify({
        'items': items,
        'total': total
    })


@articles_bp.route('/ingest/csv', methods=['POST'])
def ingest_csv_endpoint():
    """
    POST /api/ingest/csv
    
    Ingest articles from CSV file.
    Query parameters:
    - path: Path to CSV file (relative to data/ folder or absolute)
    
    Returns:
    {
        "ok": true,
        "stats": {"inserted": int, "skipped": int, "errors": int}
    }
    """
    csv_path = request.args.get('path', 'summarized_output.csv')
    
    # Resolve path
    if Path(csv_path).is_absolute():
        full_path = Path(csv_path)
    else:
        full_path = Path(Config.DATA_DIR) / csv_path
    
    if not full_path.exists():
        return jsonify({
            'ok': False,
            'error': {
                'code': 'FILE_NOT_FOUND',
                'message': f'CSV file not found: {csv_path}'
            }
        }), 404
    
    try:
        stats = ingest_csv(full_path, skip_duplicates=True)
        return jsonify({
            'ok': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': {
                'code': 'INGEST_ERROR',
                'message': str(e)
            }
        }), 500

