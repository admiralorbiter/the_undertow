"""
UMAP API endpoints.
Provides 2D UMAP projection coordinates for visualization.
"""
from flask import Blueprint, jsonify
from backend.db import get_db
from backend.config import Config

umap_bp = Blueprint('umap', __name__)


@umap_bp.route('/umap', methods=['GET'])
def get_umap():
    """
    GET /api/umap
    
    Returns 2D UMAP positions for all articles with coordinates.
    
    Response:
    {
        "points": [
            {"id": 123, "x": -3.12, "y": 1.04, "cluster_id": 7},
            ...
        ],
        "meta": {
            "model": "MiniLM-L6-v2",
            "umap": {
                "n_neighbors": 15,
                "min_dist": 0.1,
                "metric": "cosine"
            },
            "total_points": 581,
            "has_clusters": true
        }
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get all articles with UMAP coordinates
        cursor.execute("""
            SELECT id, umap_x, umap_y, cluster_id
            FROM articles
            WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
            ORDER BY id
        """)
        
        points = []
        for row in cursor.fetchall():
            points.append({
                'id': row['id'],
                'x': float(row['umap_x']) if row['umap_x'] is not None else None,
                'y': float(row['umap_y']) if row['umap_y'] is not None else None,
                'cluster_id': row['cluster_id']
            })
        
        # Check if we have clusters
        cursor.execute("SELECT COUNT(*) FROM clusters")
        has_clusters = cursor.fetchone()[0] > 0
        
        return jsonify({
            'points': points,
            'meta': {
                'model': Config.EMBEDDING_MODEL.split('/')[-1],  # Just model name
                'umap': {
                    'n_neighbors': Config.UMAP_N_NEIGHBORS,
                    'min_dist': Config.UMAP_MIN_DIST,
                    'metric': Config.UMAP_METRIC
                },
                'total_points': len(points),
                'has_clusters': has_clusters
            }
        })
    finally:
        conn.close()

