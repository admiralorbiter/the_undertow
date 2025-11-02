"""
Dashboard API endpoints
"""

from flask import Blueprint, request, jsonify
from backend.services.dashboard import DashboardService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """
    GET /api/dashboard/summary?days_back=30
    
    Returns aggregated dashboard data.
    
    Query Parameters:
        days_back: Number of days to include (default: 30, range: 7-365)
    
    Returns:
        {
            "stats": {...},
            "active_storylines": [...],
            "recent_alerts": [...],
            "temporal_heatmap": [...],
            "key_actors": [...],
            "cluster_evolution": [...]
        }
    """
    days_back = request.args.get('days_back', default=30, type=int)
    days_back = max(7, min(days_back, 365))  # Clamp to 7-365
    
    service = DashboardService()
    summary = service.get_dashboard_summary(days_back=days_back)
    
    return jsonify(summary)

