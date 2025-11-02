"""
Cluster API endpoints.
Provides cluster information and cluster-specific article lists.
"""
from flask import Blueprint, jsonify, request
from backend.db import get_db

clusters_bp = Blueprint('clusters', __name__)


@clusters_bp.route('/clusters', methods=['GET'])
def get_clusters():
    """
    GET /api/clusters
    
    Returns cluster list with metadata.
    
    Response:
    {
        "clusters": [
            {"id": 1, "label": "AI Technology", "size": 45, "score": 0.87},
            ...
        ],
        "stats": {
            "total_clusters": 10,
            "total_articles": 581,
            "unclustered": 23
        }
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get all clusters
        cursor.execute("""
            SELECT id, label, size, score
            FROM clusters
            ORDER BY size DESC, id ASC
        """)
        
        clusters = []
        for row in cursor.fetchall():
            clusters.append({
                'id': row['id'],
                'label': row['label'] or 'Unlabeled',
                'size': row['size'] or 0,
                'score': row['score']
            })
        
        # Get stats
        cursor.execute("SELECT COUNT(*) FROM clusters")
        total_clusters = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE cluster_id IS NOT NULL")
        clustered_articles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE cluster_id IS NULL")
        unclustered = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]
        
        return jsonify({
            'clusters': clusters,
            'stats': {
                'total_clusters': total_clusters,
                'total_articles': total_articles,
                'clustered_articles': clustered_articles,
                'unclustered': unclustered
            }
        })
    finally:
        conn.close()


@clusters_bp.route('/cluster/<int:cluster_id>/articles', methods=['GET'])
def get_cluster_articles(cluster_id):
    """
    GET /api/cluster/:id/articles
    
    Returns articles in a specific cluster.
    
    Query parameters:
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)
    
    Response:
    {
        "items": [article objects],
        "total": int,
        "cluster": {"id": int, "label": str, "size": int}
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)
    
    try:
        # Get cluster info
        cursor.execute("""
            SELECT id, label, size, score
            FROM clusters
            WHERE id = ?
        """, (cluster_id,))
        cluster_row = cursor.fetchone()
        
        if not cluster_row:
            return jsonify({
                'ok': False,
                'error': {
                    'code': 'CLUSTER_NOT_FOUND',
                    'message': f'Cluster {cluster_id} not found'
                }
            }), 404
        
        cluster = {
            'id': cluster_row['id'],
            'label': cluster_row['label'],
            'size': cluster_row['size'],
            'score': cluster_row['score']
        }
        
        # Get total count
        cursor.execute("""
            SELECT COUNT(*) FROM articles WHERE cluster_id = ?
        """, (cluster_id,))
        total = cursor.fetchone()[0]
        
        # Get articles
        cursor.execute("""
            SELECT id, title, summary, url, outlet, date, date_bin, cluster_id
            FROM articles
            WHERE cluster_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
        """, (cluster_id, limit, offset))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row['id'],
                'title': row['title'],
                'summary': row['summary'],
                'url': row['url'],
                'outlet': row['outlet'],
                'date': row['date'],
                'date_bin': row['date_bin'],
                'cluster_id': row['cluster_id']
            })
        
        return jsonify({
            'items': items,
            'total': total,
            'cluster': cluster
        })
    finally:
        conn.close()

