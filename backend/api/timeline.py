"""
Timeline API endpoints.
Provides temporal distribution of articles over time.
"""
from flask import Blueprint, jsonify, request
from backend.db import get_db

timeline_bp = Blueprint('timeline', __name__)


@timeline_bp.route('/timeline', methods=['GET'])
def get_timeline():
    """
    GET /api/timeline
    
    Returns article counts over time, grouped by date_bin.
    Can optionally break down by cluster.
    
    Query parameters:
    - cluster_id: Filter by specific cluster (optional)
    - group_by: 'month' or 'week' (default: uses date_bin from DB)
    
    Response:
    {
        "bins": [
            {
                "date": "2025-02",
                "count": 45,
                "by_cluster": {
                    "1": 20,
                    "2": 15,
                    "null": 10
                }
            },
            ...
        ]
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cluster_id = request.args.get('cluster_id', type=int)
        group_by = request.args.get('group_by', 'month')  # month, week, or use date_bin
        
        # Build WHERE clause
        conditions = []
        params = []
        
        if cluster_id is not None:
            conditions.append("cluster_id = ?")
            params.append(cluster_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Query to get counts grouped by date_bin
        # If no date_bin, use the date column's year-month
        if group_by == 'month':
            # Group by date_bin if available, otherwise extract year-month from date
            cursor.execute(f"""
                SELECT 
                    COALESCE(date_bin, strftime('%Y-%m', date)) as date_period,
                    COUNT(*) as count,
                    cluster_id
                FROM articles
                {where_clause}
                GROUP BY date_period, cluster_id
                ORDER BY date_period ASC
            """, params)
        else:
            # Use date_bin as-is
            cursor.execute(f"""
                SELECT 
                    date_bin as date_period,
                    COUNT(*) as count,
                    cluster_id
                FROM articles
                {where_clause}
                AND date_bin IS NOT NULL
                GROUP BY date_bin, cluster_id
                ORDER BY date_bin ASC
            """, params)
        
        rows = cursor.fetchall()
        
        # Group by date_period and aggregate by cluster
        bins_dict = {}
        
        for row in rows:
            date_period = row['date_period']
            count = row['count']
            cluster_id = row['cluster_id']
            
            if date_period not in bins_dict:
                bins_dict[date_period] = {
                    'date': date_period,
                    'count': 0,
                    'by_cluster': {}
                }
            
            bins_dict[date_period]['count'] += count
            
            # Track by cluster
            cluster_key = str(cluster_id) if cluster_id is not None else 'null'
            bins_dict[date_period]['by_cluster'][cluster_key] = \
                bins_dict[date_period]['by_cluster'].get(cluster_key, 0) + count
        
        # Convert to list and sort
        bins = sorted(bins_dict.values(), key=lambda x: x['date'])
        
        return jsonify({
            'bins': bins
        })
    finally:
        conn.close()

