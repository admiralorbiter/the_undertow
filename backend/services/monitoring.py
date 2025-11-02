"""
Monitoring Service

Implements anomaly detection for tracking unusual patterns in article flow:
- Topic surge detection
- Story reactivation alerts  
- New actor emergence
"""

import logging
import json
from datetime import datetime, timedelta
from backend.db import get_db

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for anomaly detection and alert management."""
    
    SURGE_THRESHOLD = 1.5  # >50% growth required
    
    def __init__(self):
        """Initialize monitoring service."""
        pass
    
    def run_detections(self):
        """
        Execute all detection algorithms.
        
        Returns:
            dict with summary: {'alerts_created': int, 'surges': int, 'reactivations': int, 'new_actors': int}
        """
        logger.info("Running all detection algorithms...")
        
        summary = {
            'alerts_created': 0,
            'surges': 0,
            'reactivations': 0,
            'new_actors': 0
        }
        
        try:
            # Check topic surges
            surges = self.check_topic_surges()
            summary['surges'] = len(surges)
            summary['alerts_created'] += len(surges)
            
            # Check story reactivations
            reactivations = self.check_story_reactivations()
            summary['reactivations'] = len(reactivations)
            summary['alerts_created'] += len(reactivations)
            
            # Check new actors
            new_actors = self.check_new_actors()
            summary['new_actors'] = len(new_actors)
            summary['alerts_created'] += len(new_actors)
            
            logger.info(f"Detection complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in run_detections: {e}", exc_info=True)
            raise
    
    def check_topic_surges(self):
        """
        Detect cluster/topic surges (week-over-week growth >50%).
        
        Logic:
        - Compare article counts in last 7 days vs previous 7 days
        - If (current / previous) > 1.5: SURGE
        
        Returns:
            list of alert dicts created
        """
        logger.info("Checking for topic surges...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        alerts_created = []
        
        try:
            # Get date ranges
            now = datetime.now()
            last_7d_start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            previous_7d_start = (now - timedelta(days=14)).strftime('%Y-%m-%d')
            previous_7d_end = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Get all clusters
            cursor.execute("SELECT id FROM clusters")
            cluster_ids = [row['id'] for row in cursor.fetchall()]
            
            for cluster_id in cluster_ids:
                # Count articles in last 7 days
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM articles
                    WHERE cluster_id = ? AND date >= ?
                """, (cluster_id, last_7d_start))
                current_count = cursor.fetchone()['count']
                
                if current_count == 0:
                    continue
                
                # Count articles in previous 7 days
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM articles
                    WHERE cluster_id = ? AND date >= ? AND date < ?
                """, (cluster_id, previous_7d_start, previous_7d_end))
                previous_count = cursor.fetchone()['count']
                
                if previous_count == 0:
                    # No previous activity, skip (not a surge from existing baseline)
                    continue
                
                # Check if growth exceeds threshold
                growth_ratio = current_count / previous_count
                if growth_ratio > self.SURGE_THRESHOLD:
                    # Create alert
                    entity_json = json.dumps({
                        'cluster_id': cluster_id,
                        'current_count': current_count,
                        'previous_count': previous_count,
                        'growth_ratio': growth_ratio
                    })
                    
                    description = f"Cluster {cluster_id}: {current_count} articles in last 7 days vs {previous_count} in previous week ({growth_ratio:.1f}x growth)"
                    
                    severity = 'high' if growth_ratio > 2.0 else 'medium'
                    
                    alert = self.create_alert('topic_surge', entity_json, description, severity)
                    alerts_created.append(alert)
                    
        except Exception as e:
            logger.error(f"Error checking topic surges: {e}", exc_info=True)
        
        return alerts_created
    
    def check_story_reactivations(self):
        """
        Detect dormant storylines with new activity.
        
        Logic:
        - Find storylines marked 'dormant'
        - Check if any articles in last 7 days
        - If yes: ALERT
        
        Returns:
            list of alert dicts created
        """
        logger.info("Checking for story reactivations...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        alerts_created = []
        
        try:
            # Get date range for last 7 days
            now = datetime.now()
            last_7d_start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Find dormant storylines with recent articles
            cursor.execute("""
                SELECT DISTINCT s.id, s.label, s.last_date
                FROM storylines s
                JOIN storyline_articles sa ON s.id = sa.storyline_id
                JOIN articles a ON sa.article_id = a.id
                WHERE s.status = 'dormant' AND a.date >= ?
            """, (last_7d_start,))
            
            dormant_with_recent = cursor.fetchall()
            
            for storyline in dormant_with_recent:
                # Count how many new articles
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM storyline_articles sa
                    JOIN articles a ON sa.article_id = a.id
                    WHERE sa.storyline_id = ? AND a.date >= ?
                """, (storyline['id'], last_7d_start))
                new_article_count = cursor.fetchone()['count']
                
                # Create alert
                entity_json = json.dumps({
                    'storyline_id': storyline['id'],
                    'storyline_label': storyline['label'],
                    'last_activity': storyline['last_date'],
                    'new_articles': new_article_count
                })
                
                description = f"Storyline '{storyline['label']}' (dormant since {storyline['last_date']}) has {new_article_count} new article(s)"
                
                alert = self.create_alert('story_reactivation', entity_json, description, 'medium')
                alerts_created.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking story reactivations: {e}", exc_info=True)
        
        return alerts_created
    
    def check_new_actors(self):
        """
        Detect new actor emergence (first appearance in corpus).
        
        Logic:
        - Find entities with mentions in last 7 days
        - Check if zero mentions before that window
        - If yes: ALERT
        
        Returns:
            list of alert dicts created
        """
        logger.info("Checking for new actors...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        alerts_created = []
        
        try:
            # Get date range for last 7 days
            now = datetime.now()
            last_7d_start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Find entities mentioned in last 7 days
            cursor.execute("""
                SELECT DISTINCT e.id, e.name, e.type, COUNT(DISTINCT ae.article_id) as mention_count
                FROM entities e
                JOIN article_entities ae ON e.id = ae.entity_id
                JOIN articles a ON ae.article_id = a.id
                WHERE a.date >= ?
                GROUP BY e.id, e.name, e.type
            """, (last_7d_start,))
            
            recent_entities = cursor.fetchall()
            
            for entity in recent_entities:
                # Check if this entity had any mentions before last 7 days
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM article_entities ae
                    JOIN articles a ON ae.article_id = a.id
                    WHERE ae.entity_id = ? AND a.date < ?
                """, (entity['id'], last_7d_start))
                
                historical_count = cursor.fetchone()['count']
                
                # If no historical mentions, this is a new actor
                if historical_count == 0:
                    # Create alert
                    entity_json = json.dumps({
                        'entity_id': entity['id'],
                        'entity_name': entity['name'],
                        'entity_type': entity['type'],
                        'mention_count_7d': entity['mention_count']
                    })
                    
                    description = f"New actor: {entity['name']} ({entity['type']}) appeared in {entity['mention_count']} article(s) this week"
                    
                    severity = 'medium' if entity['mention_count'] > 5 else 'low'
                    
                    alert = self.create_alert('new_actor', entity_json, description, severity)
                    alerts_created.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking new actors: {e}", exc_info=True)
        
        return alerts_created
    
    def create_alert(self, alert_type, entity_json, description, severity='medium'):
        """
        Store alert in database.
        
        Args:
            alert_type: Type of alert (topic_surge, story_reactivation, new_actor, divergence)
            entity_json: JSON string with context
            description: Human-readable description
            severity: low, medium, or high
            
        Returns:
            alert dict with id
        """
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if this exact alert already exists (avoid duplicates)
        cursor.execute("""
            SELECT id FROM alerts
            WHERE alert_type = ? AND description = ? AND triggered_at >= datetime('now', '-1 day')
        """, (alert_type, description))
        existing = cursor.fetchone()
        
        if existing:
            logger.debug(f"Alert already exists, skipping: {description[:50]}...")
            return {'id': existing['id']}
        
        # Insert new alert
        triggered_at = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO alerts (alert_type, entity_json, triggered_at, description, severity, acknowledged)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (alert_type, entity_json, triggered_at, description, severity))
        
        alert_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"Created alert: {alert_type} (id={alert_id})")
        
        return {
            'id': alert_id,
            'alert_type': alert_type,
            'description': description,
            'severity': severity
        }
    
    def get_recent_alerts(self, limit=50, since=None, alert_type=None, severity=None):
        """
        Query alerts with filters.
        
        Args:
            limit: Max number of alerts to return
            since: ISO timestamp to filter from (optional)
            alert_type: Filter by type (optional)
            severity: Filter by severity (optional)
            
        Returns:
            list of alert dicts
        """
        conn = get_db()
        cursor = conn.cursor()
        
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if since:
            query += " AND triggered_at >= ?"
            params.append(since)
        
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY triggered_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'id': row['id'],
                'alert_type': row['alert_type'],
                'entity_json': row['entity_json'],
                'triggered_at': row['triggered_at'],
                'description': row['description'],
                'severity': row['severity'],
                'acknowledged': bool(row['acknowledged'])
            })
        
        return alerts
    
    def acknowledge_alert(self, alert_id):
        """
        Mark alert as acknowledged.
        
        Args:
            alert_id: ID of alert to acknowledge
            
        Returns:
            dict with success status
        """
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE alerts SET acknowledged = 1 WHERE id = ?
        """, (alert_id,))
        
        conn.commit()
        
        return {'success': True, 'acknowledged': alert_id}

