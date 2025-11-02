"""
Monitoring API endpoints
"""

from flask import Blueprint, request, jsonify
from backend.services.monitoring import MonitoringService

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    GET /api/alerts?limit=50&since=...&alert_type=...&severity=...
    
    List recent alerts with filters.
    
    Query Parameters:
        limit: Max results (default: 50, max: 200)
        since: ISO timestamp to filter from (optional)
        alert_type: Filter by type (optional): topic_surge, story_reactivation, new_actor, divergence
        severity: Filter by severity (optional): low, medium, high
    
    Returns:
        {
            "alerts": [
                {
                    "id": 1,
                    "alert_type": "topic_surge",
                    "entity_json": "{...}",
                    "triggered_at": "2025-10-28T12:00:00",
                    "description": "...",
                    "severity": "high",
                    "acknowledged": false
                }
            ]
        }
    """
    limit = request.args.get('limit', default=50, type=int)
    limit = max(1, min(limit, 200))  # Clamp to 1-200
    
    since = request.args.get('since')
    alert_type = request.args.get('alert_type')
    severity = request.args.get('severity')
    
    service = MonitoringService()
    alerts = service.get_recent_alerts(
        limit=limit,
        since=since,
        alert_type=alert_type,
        severity=severity
    )
    
    return jsonify({'alerts': alerts})


@monitoring_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """
    POST /api/alerts/:id/acknowledge
    
    Mark alert as acknowledged.
    
    Returns:
        {"success": true, "acknowledged": alert_id}
    """
    service = MonitoringService()
    result = service.acknowledge_alert(alert_id)
    
    return jsonify(result)


@monitoring_bp.route('/monitoring/run', methods=['POST'])
def run_monitoring():
    """
    POST /api/monitoring/run
    
    Trigger detection run manually.
    
    Returns:
        {
            "alerts_created": int,
            "surges": int,
            "reactivations": int,
            "new_actors": int
        }
    """
    service = MonitoringService()
    result = service.run_detections()
    
    return jsonify(result)


@monitoring_bp.route('/monitoring/stats', methods=['GET'])
def get_monitoring_stats():
    """
    GET /api/monitoring/stats
    
    Return monitoring statistics.
    
    Returns:
        {
            "total_alerts": int,
            "unacknowledged_alerts": int,
            "recent_alerts_24h": int
        }
    """
    from backend.db import get_db
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get total alerts
    cursor.execute("SELECT COUNT(*) as count FROM alerts")
    total_alerts = cursor.fetchone()['count']
    
    # Get unacknowledged alerts
    cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE acknowledged = 0")
    unacknowledged = cursor.fetchone()['count']
    
    # Get recent alerts (last 24 hours)
    from datetime import datetime, timedelta
    last_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE triggered_at >= ?", (last_24h,))
    recent_24h = cursor.fetchone()['count']
    
    return jsonify({
        'total_alerts': total_alerts,
        'unacknowledged_alerts': unacknowledged,
        'recent_alerts_24h': recent_24h
    })

