"""
Dashboard Service

Aggregates data from multiple sources to provide a state-of-the-world
summary for the monitoring dashboard.
"""

import logging
from datetime import datetime, timedelta
from backend.db import get_db

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data aggregation."""
    
    def __init__(self):
        """Initialize dashboard service."""
        pass
    
    def get_dashboard_summary(self, days_back=30):
        """
        Aggregate dashboard data from storylines, entities, articles, clusters.
        
        Args:
            days_back: Number of days to include in temporal data
            
        Returns:
            dict with dashboard data:
            {
                "active_storylines": [...],  # Top 10 by momentum
                "recent_alerts": [],          # Empty for now (P3.2)
                "temporal_heatmap": [{date, count}],  # Last N days
                "key_actors": [{entity_id, name, type, mentions_7d}],  # Top 20
                "cluster_evolution": [{date, cluster_sizes}],
                "stats": {
                    "total_articles": int,
                    "active_storylines_count": int,
                    "dormant_storylines_count": int,
                    "total_entities": int,
                    "new_articles_7d": int
                }
            }
        """
        logger.info(f"Generating dashboard summary for last {days_back} days...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        summary = {
            "active_storylines": [],
            "recent_alerts": [],
            "temporal_heatmap": [],
            "key_actors": [],
            "cluster_evolution": [],
            "stats": {}
        }
        
        try:
            # Get cutoff dates
            now = datetime.now()
            days_back_date = (now - timedelta(days=days_back)).strftime('%Y-%m-%d')
            days_7_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Get active storylines (top 10 by momentum)
            cursor.execute("""
                SELECT id, label, status, momentum_score, article_count, first_date, last_date
                FROM storylines
                WHERE status = 'active'
                ORDER BY momentum_score DESC, last_date DESC
                LIMIT 10
            """)
            summary["active_storylines"] = [
                {
                    'id': row['id'],
                    'label': row['label'],
                    'status': row['status'],
                    'momentum_score': row['momentum_score'],
                    'article_count': row['article_count'],
                    'first_date': row['first_date'],
                    'last_date': row['last_date']
                }
                for row in cursor.fetchall()
            ]
            
            # Get temporal heatmap data (last N days)
            cursor.execute("""
                SELECT date, COUNT(*) as count
                FROM articles
                WHERE date >= ?
                GROUP BY date
                ORDER BY date ASC
            """, (days_back_date,))
            summary["temporal_heatmap"] = [
                {'date': row['date'], 'count': row['count']}
                for row in cursor.fetchall()
            ]
            
            # Get key actors (top 20 entities by mentions in last 7 days)
            cursor.execute("""
                SELECT 
                    e.id as entity_id,
                    e.name,
                    e.type,
                    COUNT(ae.article_id) as mentions_7d
                FROM entities e
                JOIN article_entities ae ON e.id = ae.entity_id
                JOIN articles a ON ae.article_id = a.id
                WHERE a.date >= ?
                GROUP BY e.id, e.name, e.type
                ORDER BY mentions_7d DESC
                LIMIT 20
            """, (days_7_ago,))
            summary["key_actors"] = [
                {
                    'entity_id': row['entity_id'],
                    'name': row['name'],
                    'type': row['type'],
                    'mentions_7d': row['mentions_7d']
                }
                for row in cursor.fetchall()
            ]
            
            # Get cluster evolution (last N days)
            cursor.execute("""
                SELECT 
                    a.date,
                    a.cluster_id,
                    COUNT(*) as count
                FROM articles a
                WHERE a.date >= ? AND a.cluster_id IS NOT NULL
                GROUP BY a.date, a.cluster_id
                ORDER BY a.date ASC, a.cluster_id ASC
            """, (days_back_date,))
            
            # Group by date
            evolution_by_date = {}
            for row in cursor.fetchall():
                date = row['date']
                if date not in evolution_by_date:
                    evolution_by_date[date] = {}
                evolution_by_date[date][row['cluster_id']] = row['count']
            
            # Convert to list format
            summary["cluster_evolution"] = [
                {'date': date, 'cluster_sizes': cluster_sizes}
                for date, cluster_sizes in evolution_by_date.items()
            ]
            
            # Get stats
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM storylines WHERE status = 'active'")
            active_storylines_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM storylines WHERE status = 'dormant'")
            dormant_storylines_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM articles WHERE date >= ?", (days_7_ago,))
            new_articles_7d = cursor.fetchone()[0]
            
            # Get unacknowledged alerts count
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = 0")
            unacknowledged_alerts = cursor.fetchone()[0]
            
            summary["stats"] = {
                "total_articles": total_articles,
                "active_storylines_count": active_storylines_count,
                "dormant_storylines_count": dormant_storylines_count,
                "total_entities": total_entities,
                "new_articles_7d": new_articles_7d,
                "unacknowledged_alerts": unacknowledged_alerts
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard summary: {e}", exc_info=True)
        finally:
            conn.close()
        
        logger.info("Dashboard summary generated successfully")
        return summary

