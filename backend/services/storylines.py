"""
Story Arc Detection Service

Implements multi-tier storyline threading to group related articles
and track narrative evolution over time.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
import json
from backend.db import get_db

logger = logging.getLogger(__name__)


class StorylineService:
    """Service for storyline detection and management."""
    
    TIER1_THRESHOLD = 0.85  # Near-duplicates
    TIER1_WINDOW_DAYS = 3
    
    TIER2_THRESHOLD_LOW = 0.65  # Continuations
    TIER2_THRESHOLD_HIGH = 0.85
    TIER2_WINDOW_DAYS = 7
    
    TIER3_THRESHOLD_LOW = 0.50  # Related
    TIER3_THRESHOLD_HIGH = 0.65
    
    def __init__(self):
        """Initialize storylines service."""
        pass
    
    def build_storylines(self, force_recompute=False):
        """
        Build all storylines from existing similarities.
        
        Process:
        1. Load all similarity edges from database
        2. Group by tier based on cosine and temporal proximity
        3. Union-Find to connect articles into storylines
        4. Assign sequences and generate labels
        5. Calculate momentum scores and status
        
        Args:
            force_recompute: If True, rebuild even if storylines exist
            
        Returns:
            dict with stats: {'storylines_created': int, 'articles_grouped': int}
        """
        logger.info("Building storylines from similarities...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if storylines already exist
        if not force_recompute:
            cursor.execute("SELECT COUNT(*) FROM storylines")
            if cursor.fetchone()[0] > 0:
                logger.info("Storylines already exist, skipping")
                return {'status': 'skipped', 'storylines_created': 0, 'articles_grouped': 0}
        
        # Load all similarity edges
        cursor.execute("""
            SELECT src_id, dst_id, cosine, shared_entities
            FROM similarities
            ORDER BY cosine DESC
        """)
        edges = cursor.fetchall()
        
        logger.info(f"Loaded {len(edges)} similarity edges")
        
        # Get all articles with dates
        cursor.execute("SELECT id, date FROM articles")
        article_dates = {row['id']: row['date'] for row in cursor.fetchall()}
        
        # Build graph by tier
        tier1_edges = []
        tier2_edges = []
        tier3_edges = []
        
        for edge in edges:
            src_id, dst_id, cosine, shared_entities_raw = edge['src_id'], edge['dst_id'], edge['cosine'], edge['shared_entities']
            
            # Skip self-loops
            if src_id == dst_id:
                continue
            
            src_date = article_dates[src_id]
            dst_date = article_dates[dst_id]
            
            # Calculate days apart
            try:
                src_dt = datetime.fromisoformat(src_date)
                dst_dt = datetime.fromisoformat(dst_date)
                days_apart = abs((src_dt - dst_dt).days)
            except (ValueError, AttributeError):
                # Date parsing error, skip this edge
                continue
            
            # Categorize edge
            if cosine >= self.TIER1_THRESHOLD and days_apart <= self.TIER1_WINDOW_DAYS:
                tier1_edges.append((src_id, dst_id, 'tier1'))
            elif (self.TIER2_THRESHOLD_LOW <= cosine < self.TIER2_THRESHOLD_HIGH 
                  and days_apart <= self.TIER2_WINDOW_DAYS):
                tier2_edges.append((src_id, dst_id, 'tier2'))
            elif self.TIER3_THRESHOLD_LOW <= cosine < self.TIER3_THRESHOLD_HIGH:
                # Check for shared entities
                try:
                    shared_entities = json.loads(shared_entities_raw) if shared_entities_raw else []
                    if isinstance(shared_entities, list) and len(shared_entities) >= 2:
                        tier3_edges.append((src_id, dst_id, 'tier3'))
                except (json.JSONDecodeError, TypeError):
                    # Invalid JSON, skip tier3
                    pass
        
        logger.info(f"Categorized edges: Tier1={len(tier1_edges)}, Tier2={len(tier2_edges)}, Tier3={len(tier3_edges)}")
        
        # Union-Find to group articles into storylines
        storyline_map = {}  # article_id -> storyline_id
        
        # Process tier1: strict grouping
        storyline_counter = 1
        for src_id, dst_id, tier in tier1_edges:
            if src_id not in storyline_map and dst_id not in storyline_map:
                # New storyline
                new_id = storyline_counter
                storyline_counter += 1
                storyline_map[src_id] = new_id
                storyline_map[dst_id] = new_id
            elif src_id in storyline_map:
                storyline_map[dst_id] = storyline_map[src_id]
            elif dst_id in storyline_map:
                storyline_map[src_id] = storyline_map[dst_id]
        
        # Process tier2: add to existing or create new
        for src_id, dst_id, tier in tier2_edges:
            if src_id in storyline_map:
                storyline_map[dst_id] = storyline_map[src_id]
            elif dst_id in storyline_map:
                storyline_map[src_id] = storyline_map[dst_id]
            else:
                # Create new storyline for tier2
                new_id = storyline_counter
                storyline_counter += 1
                storyline_map[src_id] = new_id
                storyline_map[dst_id] = new_id
        
        # Process tier3: prefer adding to existing
        for src_id, dst_id, tier in tier3_edges:
            if src_id not in storyline_map and dst_id not in storyline_map:
                # New standalone storyline
                new_id = storyline_counter
                storyline_counter += 1
                storyline_map[src_id] = new_id
                storyline_map[dst_id] = new_id
            elif src_id in storyline_map:
                storyline_map[dst_id] = storyline_map[src_id]
            elif dst_id in storyline_map:
                storyline_map[src_id] = storyline_map[dst_id]
        
        logger.info(f"Created {storyline_counter - 1} storylines from {len(storyline_map)} articles")
        
        # Create storylines in database
        storyline_groups = defaultdict(list)
        for article_id, storyline_id in storyline_map.items():
            storyline_groups[storyline_id].append(article_id)
        
        storylines_created = 0
        
        for storyline_id, article_ids in storyline_groups.items():
            # Get date range and article count
            dates = []
            for aid in article_ids:
                if aid in article_dates:
                    dates.append(article_dates[aid])
            
            if not dates:
                continue
                
            first_date = min(dates)
            last_date = max(dates)
            
            # Generate label from first article's title
            try:
                cursor.execute("SELECT title FROM articles WHERE id = ?", (article_ids[0],))
                first_title_row = cursor.fetchone()
                if first_title_row:
                    first_title = first_title_row[0]
                else:
                    first_title = f"Storyline {storyline_id}"
            except Exception as e:
                logger.error(f"Error getting title for article {article_ids[0]}: {e}")
                first_title = f"Storyline {storyline_id}"
            
            label = self._generate_label(first_title)
            
            # Insert storyline
            cursor.execute("""
                INSERT INTO storylines (id, label, status, first_date, last_date, article_count)
                VALUES (?, ?, 'active', ?, ?, ?)
            """, (storyline_id, label, first_date, last_date, len(article_ids)))
            
            # Insert storyline_articles with sequence
            sorted_articles = sorted(article_ids, key=lambda aid: article_dates.get(aid, ''))
            for seq, article_id in enumerate(sorted_articles):
                # Determine tier for this article in this storyline
                cursor.execute("""
                    INSERT INTO storyline_articles (storyline_id, article_id, tier, sequence_order)
                    VALUES (?, ?, 'tier1', ?)
                """, (storyline_id, article_id, seq))
                
                # Update articles table
                cursor.execute("""
                    UPDATE articles SET storyline_id = ? WHERE id = ?
                """, (storyline_id, article_id))
            
            storylines_created += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created {storylines_created} storylines in database")
        
        # Update momentum scores and status
        self._update_momentum_scores()
        
        return {
            'status': 'completed',
            'storylines_created': storylines_created,
            'articles_grouped': len(storyline_map)
        }
    
    def _generate_label(self, title):
        """
        Generate a short label from article title.
        
        Args:
            title: Article title
            
        Returns:
            str: Short label (max 60 chars)
        """
        # Simple heuristic: truncate to 60 chars
        if len(title) <= 60:
            return title
        return title[:57] + "..."
    
    def _update_momentum_scores(self):
        """
        Update momentum scores and status for all storylines.
        
        Called after storyline creation or when new articles added.
        """
        logger.info("Updating momentum scores...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all storylines
        cursor.execute("SELECT id, first_date, last_date FROM storylines")
        storylines = cursor.fetchall()
        
        for storyline in storylines:
            storyline_id = storyline['id']
            
            try:
                last_date = datetime.fromisoformat(storyline['last_date'])
                first_date_dt = datetime.fromisoformat(storyline['first_date'])
            except (ValueError, AttributeError):
                # Invalid date format, skip
                continue
            
            # Get articles in this storyline
            cursor.execute("""
                SELECT a.id, a.date
                FROM articles a
                WHERE a.storyline_id = ?
                ORDER BY a.date DESC
            """, (storyline_id,))
            articles = cursor.fetchall()
            
            # Calculate momentum
            now = datetime.now()
            momentum = 0.0
            
            for article in articles:
                try:
                    article_date = datetime.fromisoformat(article['date'])
                    days_ago = (now - article_date).days
                    
                    if days_ago <= 7:
                        momentum += 1.0
                    elif days_ago <= 14:
                        momentum += 0.5
                    elif days_ago <= 30:
                        momentum += 0.25
                except (ValueError, AttributeError):
                    # Invalid date, skip
                    continue
            
            # Normalize by duration (days)
            duration = (last_date - first_date_dt).days
            if duration > 0:
                momentum /= duration
            else:
                momentum = 0.0
            
            # Determine status
            days_since_last = (now - last_date).days
            if momentum > 0.5 and days_since_last <= 7:
                status = 'active'
            elif momentum > 0 and days_since_last <= 14:
                status = 'active'
            elif days_since_last > 14:
                status = 'dormant'
            else:
                status = 'concluded'
            
            # Update storyline
            cursor.execute("""
                UPDATE storylines
                SET momentum_score = ?, status = ?
                WHERE id = ?
            """, (momentum, status, storyline_id))
        
        conn.commit()
        conn.close()
        
        logger.info("Updated momentum scores")
    
    def get_storyline_stats(self):
        """
        Get statistics about storylines.
        
        Returns:
            dict with counts by status
        """
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT status, COUNT(*) as count FROM storylines GROUP BY status")
        stats = {row['status']: row['count'] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) FROM storylines")
        stats['total'] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats

