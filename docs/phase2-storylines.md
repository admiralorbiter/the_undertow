# Phase 2: Story Arc Detection

## Overview

Track how individual news stories evolve and branch over time using multi-tier storyline threading. Stories are grouped by relationship strength and temporal proximity, providing a narrative evolution view.

## Goals

- Detect near-duplicate articles (same event, different outlets)
- Find story continuations (same topic advancing in time)
- Identify related developments (connected but diverging narratives)
- Calculate momentum scores to track active vs. dormant storylines
- Visualize storylines as flowing rivers/timelines

## Technical Design

### Database Schema

**Table: `storylines`**
```sql
CREATE TABLE storylines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    status TEXT CHECK(status IN ('active', 'dormant', 'concluded')),
    momentum_score REAL DEFAULT 0.0,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL,
    article_count INTEGER DEFAULT 0
);
```

**Table: `storyline_articles`**
```sql
CREATE TABLE storyline_articles (
    storyline_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    tier TEXT CHECK(tier IN ('tier1', 'tier2', 'tier3')),
    sequence_order INTEGER NOT NULL,
    PRIMARY KEY (storyline_id, article_id),
    FOREIGN KEY (storyline_id) REFERENCES storylines(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

**Modify `articles` table:**
```sql
ALTER TABLE articles ADD COLUMN storyline_id INTEGER REFERENCES storylines(id);
CREATE INDEX idx_articles_storyline ON articles(storyline_id);
```

### Storyline Tier Definitions

**Tier 1: Near-Duplicates**
- Similarity: `cosine >= 0.85`
- Temporal window: `|date_i - date_j| <= 3 days`
- Typical: Same event, different outlets/angles

**Tier 2: Continuations**
- Similarity: `0.65 <= cosine < 0.85`
- Temporal window: `|date_i - date_j| <= 7 days`
- Typical: Same topic advancing, story developments

**Tier 3: Related**
- Similarity: `0.50 <= cosine < 0.65`
- Shared key entities: at least 2 overlapping entities
- No strict temporal window
- Typical: Connected but diverging narratives

### Momentum Scoring

Formula for each storyline:
```
momentum_score = Σ(article_frequency * recency_weight)

Where:
- article_frequency = articles per day in recent window
- recency_weight = 1.0 for last 7 days, 0.5 for 7-14 days, 0.25 for 14-30 days
- normalized by storyline duration
```

Status determination:
- **Active**: momentum_score > 0.5 AND last_date within 7 days
- **Dormant**: momentum_score > 0 AND last_date > 14 days ago
- **Concluded**: momentum_score = 0 OR no articles in 30 days

## Service Implementation

**File:** `backend/services/storylines.py`

```python
"""
Story Arc Detection Service

Implements multi-tier storyline threading to group related articles
and track narrative evolution over time.
"""

import logging
from datetime import datetime, timedelta
from backend.db import get_db
from backend.config import Config

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
            src_id, dst_id, cosine, shared_entities = edge[0], edge[1], edge[2], edge[3]
            
            # Skip self-loops
            if src_id == dst_id:
                continue
            
            src_date = article_dates[src_id]
            dst_date = article_dates[dst_id]
            
            # Calculate days apart
            src_dt = datetime.fromisoformat(src_date)
            dst_dt = datetime.fromisoformat(dst_date)
            days_apart = abs((src_dt - dst_dt).days)
            
            # Categorize edge
            if cosine >= self.TIER1_THRESHOLD and days_apart <= self.TIER1_WINDOW_DAYS:
                tier1_edges.append((src_id, dst_id, 'tier1'))
            elif (self.TIER2_THRESHOLD_LOW <= cosine < self.TIER2_THRESHOLD_HIGH 
                  and days_apart <= self.TIER2_WINDOW_DAYS):
                tier2_edges.append((src_id, dst_id, 'tier2'))
            elif self.TIER3_THRESHOLD_LOW <= cosine < self.TIER3_THRESHOLD_HIGH:
                # Check for shared entities
                if shared_entities and len(shared_entities) >= 2:
                    tier3_edges.append((src_id, dst_id, 'tier3'))
        
        logger.info(f"Categorized edges: Tier1={len(tier1_edges)}, Tier2={len(tier2_edges)}, Tier3={len(tier3_edges)}")
        
        # Union-Find to group articles into storylines
        # Start with tier1, then connect tier2 and tier3 to existing groups
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
                # Check if we should create new storyline for tier2
                # Only if there are strong enough connections
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
        
        logger.info(f"Created {storyline_counter - 1} storylines")
        
        # Create storylines in database
        # First, get article groups
        from collections import defaultdict
        storyline_groups = defaultdict(list)
        for article_id, storyline_id in storyline_map.items():
            storyline_groups[storyline_id].append(article_id)
        
        storylines_created = 0
        
        for storyline_id, article_ids in storyline_groups.items():
            # Get date range and article count
            dates = [article_dates[aid] for aid in article_ids]
            first_date = min(dates)
            last_date = max(dates)
            
            # Generate label from first article's title
            cursor.execute("SELECT title FROM articles WHERE id = ?", (article_ids[0],))
            first_title = cursor.fetchone()[0]
            label = self._generate_label(first_title)
            
            # Insert storyline
            cursor.execute("""
                INSERT INTO storylines (id, label, status, first_date, last_date, article_count)
                VALUES (?, ?, 'active', ?, ?, ?)
            """, (storyline_id, label, first_date, last_date, len(article_ids)))
            
            # Insert storyline_articles with sequence
            sorted_articles = sorted(article_ids, key=lambda aid: article_dates[aid])
            for seq, article_id in enumerate(sorted_articles):
                # Determine tier for this article in this storyline
                # Simplified: use tier1 for now
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
        
        logger.info(f"Created {storylines_created} storylines")
        
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
            last_date = datetime.fromisoformat(storyline['last_date'])
            
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
            recent_count = 0
            
            for article in articles:
                article_date = datetime.fromisoformat(article['date'])
                days_ago = (now - article_date).days
                
                if days_ago <= 7:
                    momentum += 1.0
                    recent_count += 1
                elif days_ago <= 14:
                    momentum += 0.5
                elif days_ago <= 30:
                    momentum += 0.25
            
            # Normalize by duration (days)
            duration = (last_date - datetime.fromisoformat(storyline['first_date'])).days
            if duration > 0:
                momentum /= duration
            
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
```

## API Implementation

**File:** `backend/api/storylines.py`

```python
"""
Storylines API endpoints
"""

from flask import Blueprint, request, jsonify
from backend.db import get_db

storylines_bp = Blueprint('storylines', __name__)


@storylines_bp.route('/storylines', methods=['GET'])
def get_storylines():
    """
    GET /api/storylines
    
    Query: status, min_momentum, from_date, to_date
    
    Returns: { storylines: [{id, label, status, momentum_score, article_count, first_date, last_date}] }
    """
    status = request.args.get('status')
    min_momentum = request.args.get('min_momentum', type=float)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Build query
    conditions = []
    params = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if min_momentum is not None:
        conditions.append("momentum_score >= ?")
        params.append(min_momentum)
    
    if from_date:
        conditions.append("first_date >= ?")
        params.append(from_date)
    
    if to_date:
        conditions.append("first_date <= ?")
        params.append(to_date)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    cursor.execute(f"""
        SELECT id, label, status, momentum_score, article_count, first_date, last_date
        FROM storylines
        {where_clause}
        ORDER BY momentum_score DESC, last_date DESC
    """, params)
    
    storylines = []
    for row in cursor.fetchall():
        storylines.append({
            'id': row['id'],
            'label': row['label'],
            'status': row['status'],
            'momentum_score': row['momentum_score'],
            'article_count': row['article_count'],
            'first_date': row['first_date'],
            'last_date': row['last_date']
        })
    
    conn.close()
    
    return jsonify({'storylines': storylines})


@storylines_bp.route('/storyline/<int:storyline_id>/articles', methods=['GET'])
def get_storyline_articles(storyline_id):
    """
    GET /api/storyline/:id/articles
    
    Returns: { storyline: {...}, articles: [{id, title, date, tier, sequence_order}] }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get storyline info
    cursor.execute("""
        SELECT id, label, status, momentum_score, first_date, last_date
        FROM storylines
        WHERE id = ?
    """, (storyline_id,))
    
    storyline_row = cursor.fetchone()
    if not storyline_row:
        conn.close()
        return jsonify({'ok': False, 'error': {'code': 'NOT_FOUND', 'message': 'Storyline not found'}}), 404
    
    storyline = {
        'id': storyline_row['id'],
        'label': storyline_row['label'],
        'status': storyline_row['status'],
        'momentum_score': storyline_row['momentum_score'],
        'first_date': storyline_row['first_date'],
        'last_date': storyline_row['last_date']
    }
    
    # Get articles
    cursor.execute("""
        SELECT a.id, a.title, a.date, sa.tier, sa.sequence_order
        FROM articles a
        JOIN storyline_articles sa ON a.id = sa.article_id
        WHERE sa.storyline_id = ?
        ORDER BY sa.sequence_order
    """, (storyline_id,))
    
    articles = []
    for row in cursor.fetchall():
        articles.append({
            'id': row['id'],
            'title': row['title'],
            'date': row['date'],
            'tier': row['tier'],
            'sequence_order': row['sequence_order']
        })
    
    conn.close()
    
    return jsonify({'storyline': storyline, 'articles': articles})
```

## Frontend Visualization

**File:** `static/js/views/storylines.js`

```javascript
/**
 * Storylines View - River/Sankey visualization
 */

export class StorylinesView {
    constructor(container) {
        this.container = container;
        this.chart = null;
        this.data = null;
    }
    
    async load() {
        console.log('Loading Storylines View...');
        
        try {
            // Fetch storylines list
            const response = await fetch('/api/storylines?status=active&min_momentum=0.1');
            if (!response.ok) throw new Error(`API error: ${response.status}`);
            
            const data = await response.json();
            this.data = data;
            
            this.render(data);
        } catch (error) {
            console.error('Error loading storylines:', error);
            this.container.innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #ef4444;">
                    <h3>Error Loading Storylines</h3>
                    <p>${error.message}</p>
                </div>
            `;
        }
    }
    
    render(data) {
        if (!window.echarts) {
            console.error('ECharts not loaded');
            return;
        }
        
        // TODO: Implement river plot visualization
        // For now, render as stacked timeline
        
        this.container.innerHTML = `
            <div style="padding: 2rem;">
                <h2>Active Storylines</h2>
                <div id="storylines-list"></div>
            </div>
        `;
        
        const listContainer = document.getElementById('storylines-list');
        
        // Render storylines as cards
        data.storylines.forEach(storyline => {
            const card = document.createElement('div');
            card.className = 'storyline-card';
            card.style.cssText = 'border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; border-radius: 4px; cursor: pointer;';
            
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3 style="margin: 0 0 0.5rem;">${storyline.label}</h3>
                        <p style="margin: 0; color: #666;">
                            ${storyline.article_count} articles | 
                            ${storyline.status} | 
                            Momentum: ${storyline.momentum_score.toFixed(2)}
                        </p>
                    </div>
                    <div style="color: #999; font-size: 0.9rem;">
                        ${storyline.first_date} → ${storyline.last_date}
                    </div>
                </div>
            `;
            
            card.addEventListener('click', () => {
                this.showStorylineDetails(storyline.id);
            });
            
            listContainer.appendChild(card);
        });
    }
    
    async showStorylineDetails(storylineId) {
        try {
            const response = await fetch(`/api/storyline/${storylineId}/articles`);
            const data = await response.json();
            
            // TODO: Open modal or details panel
            console.log('Storyline details:', data);
        } catch (error) {
            console.error('Error fetching storyline details:', error);
        }
    }
}
```

## Testing

**File:** `tests/unit/test_storylines.py`

```python
"""
Tests for storyline detection service
"""

import pytest
from datetime import datetime, timedelta
from backend.services.storylines import StorylineService


def test_tier1_near_duplicate():
    """Test Tier 1 near-duplicate detection."""
    service = StorylineService()
    
    # Articles should be linked if cosine >= 0.85 and within 3 days
    assert service._should_link_tier1(0.9, 1) == True
    assert service._should_link_tier1(0.8, 1) == False  # Below threshold
    assert service._should_link_tier1(0.9, 5) == False  # Too far apart


def test_momentum_calculation():
    """Test momentum score calculation."""
    # TODO: Add test cases
    pass
```

## Integration

Update `backend/services/pipeline.py`:

```python
def step_storylines(self, force_recompute=False):
    """Step 9: Storyline threading."""
    logger.info("Step 9: Building storylines...")
    
    from backend.services.storylines import StorylineService
    
    service = StorylineService()
    stats = service.build_storylines(force_recompute=force_recompute)
    
    if stats.get('status') != 'skipped' and stats.get('storylines_created', 0) > 0:
        self.steps_completed.add(9)
    
    return stats
```

## Next Steps

1. Implement Union-Find algorithm properly (currently simplified)
2. Add storyline merging logic for overlapping narratives
3. Implement river plot visualization in frontend
4. Add storyline comparison features
5. Test on real data
