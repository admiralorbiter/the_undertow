# Phase 2: Entity Tracking & NER

## Overview

Extract named entities (People, Organizations, Places) from articles and track their mentions over time. Classify entity roles (protagonist, antagonist, subject, adjudicator) within each article to understand their involvement in narratives.

## Goals

- Extract PERSON, ORG, GPE entities using spaCy
- Track entity mentions chronologically per article
- Classify entity roles (who's doing what)
- Build entity timeline and relationship views
- Filter articles by entity

## Technical Design

### Database Schema

**Table: `entities`** (already exists, may need modification)
```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('PERSON', 'ORG', 'GPE', 'LOC', 'MISC', 'OTHER')) NOT NULL,
    canonical_name TEXT  -- For disambiguation later
);

CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_type ON entities(type);
```

**Table: `article_entities`** (already exists, may need modification)
```sql
CREATE TABLE article_entities (
    article_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    count INTEGER DEFAULT 1,  -- How many times mentioned in article
    first_mention_char INTEGER,  -- Position in text
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (article_id, entity_id),
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);
```

**Table: `entity_roles`** (NEW)
```sql
CREATE TABLE entity_roles (
    entity_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    role_type TEXT CHECK(role_type IN ('protagonist', 'antagonist', 'subject', 'adjudicator', 'neutral')) NOT NULL,
    confidence REAL DEFAULT 0.5,
    evidence TEXT,  -- JSON with evidence (sentences, verb patterns)
    PRIMARY KEY (entity_id, article_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE INDEX idx_entity_roles_article ON entity_roles(article_id);
CREATE INDEX idx_entity_roles_entity ON entity_roles(entity_id);
```

### Entity Stop List

Filter out common/generic entities that don't add value:
- Generic locations: "United States", "America", "US", "USA", "North America"
- Generic organizations: "Congress", "House", "Senate", "White House"
- Time references: "Monday", "Tuesday", "January", "February", "2025"
- Common words that get tagged: "Trump Administration", "Biden Administration"

## Service Implementation

**File:** `backend/services/ner.py`

```python
"""
Named Entity Recognition Service

Extracts entities from articles, tracks mentions, and classifies roles.
"""

import logging
import spacy
from collections import Counter
from typing import List, Dict, Tuple
from backend.db import get_db
from backend.config import Config

logger = logging.getLogger(__name__)


# Entity stop list - common entities to filter out
ENTITY_STOPLIST = {
    'PERSON': set(),  # Could add titles like "President"
    'ORG': {'Congress', 'House', 'Senate', 'White House', 'Capital'},
    'GPE': {'United States', 'America', 'US', 'USA', 'North America', 
            'the United States', 'United States of America'},
    'LOC': {'United States', 'America'},
    'MISC': set(),
}

# Causal/action language patterns for role classification
PROTAGONIST_PATTERNS = [
    r'\b(announced|ordered|signed|issued|declared|decided|acted|launched|introduced)\b',
    r'\b(ordered|directed|instructed|commanded|requested|demanded)\b',
    r'\b(initiated|started|began|commenced|created|established)\b',
]

ANTAGONIST_PATTERNS = [
    r'\b(criticized|opposed|challenged|fought|resisted|blocked|rejected)\b',
    r'\b(denounced|condemned|attacked|threatened|warned)\b',
]

SUBJECT_PATTERNS = [
    r'\b(affected|impacted|impact|affected by|suffered|experienced)\b',
    r'\b(targeted|target|victim|recipient)\b',
]

ADJUDICATOR_PATTERNS = [
    r'\b(ruled|decided|determined|found|held|concluded)\b',
    r'\b(judge|court|supreme court|federal court|appeals court)\b',
]


class NERService:
    """Service for Named Entity Recognition and role classification."""
    
    def __init__(self):
        """Initialize NER service with spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model: en_core_web_sm")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Please run: python -m spacy download en_core_web_sm")
            raise
    
    def extract_entities(self, force_recompute=False):
        """
        Extract entities from all articles.
        
        Process:
        1. Load articles without entities
        2. Run NER on title + summary
        3. Filter stoplist entities
        4. Upsert entities table
        5. Link articles to entities
        6. Count mentions
        
        Args:
            force_recompute: If True, re-extract even if entities exist
            
        Returns:
            dict with stats: {'articles_processed': int, 'entities_found': int}
        """
        logger.info("Extracting entities from articles...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get articles to process
        if force_recompute:
            cursor.execute("SELECT id, title, summary FROM articles")
        else:
            cursor.execute("""
                SELECT a.id, a.title, a.summary
                FROM articles a
                LEFT JOIN article_entities ae ON a.id = ae.article_id
                WHERE ae.article_id IS NULL
            """)
        
        articles = cursor.fetchall()
        logger.info(f"Processing {len(articles)} articles")
        
        articles_processed = 0
        entities_found = 0
        entity_name_to_id = {}
        
        # Load existing entities
        cursor.execute("SELECT id, name FROM entities")
        for row in cursor.fetchall():
            entity_name_to_id[row['name']] = row['id']
        
        import re
        
        for article in articles:
            article_id = article['id']
            text = f"{article['title']}\n\n{article['summary']}"
            
            # Run spaCy NER
            doc = self.nlp(text)
            
            # Extract entities
            article_entities = {}  # entity_name -> {type, count, first_char}
            
            for ent in doc.ents:
                # Filter by type and stoplist
                if ent.label_ not in ['PERSON', 'ORG', 'GPE', 'LOC', 'MISC']:
                    continue
                
                entity_name = ent.text.strip()
                
                # Check stoplist
                if self._is_stop_entity(entity_name, ent.label_):
                    continue
                
                # Track in article
                if entity_name not in article_entities:
                    article_entities[entity_name] = {
                        'type': ent.label_,
                        'count': 0,
                        'first_char': ent.start_char
                    }
                article_entities[entity_name]['count'] += 1
            
            # Upsert entities and link to article
            for entity_name, info in article_entities.items():
                # Upsert entity
                if entity_name not in entity_name_to_id:
                    cursor.execute("""
                        INSERT INTO entities (name, type)
                        VALUES (?, ?)
                    """, (entity_name, info['type']))
                    entity_id = cursor.lastrowid
                    entity_name_to_id[entity_name] = entity_id
                    entities_found += 1
                else:
                    entity_id = entity_name_to_id[entity_name]
                
                # Link to article
                cursor.execute("""
                    INSERT OR IGNORE INTO article_entities (article_id, entity_id, count, first_mention_char)
                    VALUES (?, ?, ?, ?)
                """, (article_id, entity_id, info['count'], info['first_char']))
            
            articles_processed += 1
            
            if articles_processed % 100 == 0:
                logger.info(f"Processed {articles_processed} articles...")
                conn.commit()
        
        conn.commit()
        conn.close()
        
        logger.info(f"Processed {articles_processed} articles, found {entities_found} new entities")
        
        return {
            'status': 'completed',
            'articles_processed': articles_processed,
            'entities_found': entities_found
        }
    
    def _is_stop_entity(self, name: str, entity_type: str) -> bool:
        """Check if entity is in stoplist."""
        stoplist = ENTITY_STOPLIST.get(entity_type, set())
        
        # Case-insensitive check
        name_lower = name.lower().strip()
        
        for stop_name in stoplist:
            if stop_name.lower() == name_lower:
                return True
        
        # Additional heuristic: very short entities are often noise
        if len(name) <= 2:
            return True
        
        return False
    
    def classify_entity_roles(self, force_recompute=False):
        """
        Classify entity roles in articles.
        
        Process:
        1. For each article-entity pair, analyze context
        2. Detect action/verb patterns near entity mentions
        3. Assign role based on patterns
        4. Store in entity_roles table
        
        Args:
            force_recompute: If True, re-classify even if roles exist
            
        Returns:
            dict with stats: {'roles_classified': int}
        """
        logger.info("Classifying entity roles...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get articles with entities
        cursor.execute("""
            SELECT DISTINCT a.id, a.title, a.summary, e.id as entity_id, e.name as entity_name
            FROM articles a
            JOIN article_entities ae ON a.id = ae.article_id
            JOIN entities e ON ae.entity_id = e.id
            ORDER BY a.id
        """)
        
        article_entities = cursor.fetchall()
        logger.info(f"Classifying roles for {len(article_entities)} article-entity pairs")
        
        roles_classified = 0
        import re
        
        for row in article_entities:
            article_id = row['id']
            entity_id = row['entity_id']
            entity_name = row['entity_name']
            text = f"{row['title']}\n\n{row['summary']}"
            
            # Skip if already classified
            if not force_recompute:
                cursor.execute("""
                    SELECT 1 FROM entity_roles
                    WHERE article_id = ? AND entity_id = ?
                """, (article_id, entity_id))
                if cursor.fetchone():
                    continue
            
            # Extract sentences containing entity
            doc = self.nlp(text)
            entity_sentences = []
            
            for sent in doc.sents:
                if entity_name.lower() in sent.text.lower():
                    entity_sentences.append(sent.text)
            
            if not entity_sentences:
                continue
            
            # Analyze patterns
            role_type, confidence = self._classify_role(text, entity_name, entity_sentences)
            
            # Store role
            cursor.execute("""
                INSERT OR REPLACE INTO entity_roles (entity_id, article_id, role_type, confidence)
                VALUES (?, ?, ?, ?)
            """, (entity_id, article_id, role_type, confidence))
            
            roles_classified += 1
            
            if roles_classified % 100 == 0:
                conn.commit()
        
        conn.commit()
        conn.close()
        
        logger.info(f"Classified {roles_classified} entity roles")
        
        return {
            'status': 'completed',
            'roles_classified': roles_classified
        }
    
    def _classify_role(self, text: str, entity_name: str, sentences: List[str]) -> Tuple[str, float]:
        """
        Classify role of entity based on context patterns.
        
        Args:
            text: Full article text
            entity_name: Name of entity
            sentences: Sentences containing entity
            
        Returns:
            Tuple of (role_type, confidence)
        """
        # Count pattern matches
        protagonist_score = 0
        antagonist_score = 0
        subject_score = 0
        adjudicator_score = 0
        
        import re
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check protagonist patterns
            for pattern in PROTAGONIST_PATTERNS:
                if re.search(pattern, sentence_lower):
                    protagonist_score += 1
            
            # Check antagonist patterns
            for pattern in ANTAGONIST_PATTERNS:
                if re.search(pattern, sentence_lower):
                    antagonist_score += 1
            
            # Check subject patterns
            for pattern in SUBJECT_PATTERNS:
                if re.search(pattern, sentence_lower):
                    subject_score += 1
            
            # Check adjudicator patterns
            for pattern in ADJUDICATOR_PATTERNS:
                if re.search(pattern, sentence_lower):
                    adjudicator_score += 1
        
        # Determine role
        scores = {
            'protagonist': protagonist_score,
            'antagonist': antagonist_score,
            'subject': subject_score,
            'adjudicator': adjudicator_score
        }
        
        max_role = max(scores.items(), key=lambda x: x[1])
        
        if max_role[1] == 0:
            return ('neutral', 0.5)
        
        # Confidence based on score dominance
        total_score = sum(scores.values())
        confidence = max_role[1] / total_score if total_score > 0 else 0.5
        
        return (max_role[0], min(confidence, 0.95))
```

## API Implementation

**File:** `backend/api/entities.py`

```python
"""
Entities API endpoints
"""

from flask import Blueprint, request, jsonify
from backend.db import get_db

entities_bp = Blueprint('entities', __name__)


@entities_bp.route('/entities', methods=['GET'])
def get_entities():
    """
    GET /api/entities
    
    Query: type, q (search), min_degree (articles mentioned in)
    
    Returns: { items: [{id, name, type, degree}] }
    """
    entity_type = request.args.get('type')
    query = request.args.get('q', '').strip()
    min_degree = request.args.get('min_degree', type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Build query
    conditions = []
    params = []
    
    if entity_type:
        conditions.append("e.type = ?")
        params.append(entity_type)
    
    if query:
        conditions.append("e.name LIKE ?")
        params.append(f"%{query}%")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get entities with degree (article count)
    cursor.execute(f"""
        SELECT e.id, e.name, e.type, COUNT(ae.article_id) as degree
        FROM entities e
        LEFT JOIN article_entities ae ON e.id = ae.entity_id
        {where_clause}
        GROUP BY e.id, e.name, e.type
        HAVING degree >= COALESCE(?, 0)
        ORDER BY degree DESC
        LIMIT 500
    """, params + [min_degree if min_degree else 0])
    
    entities = []
    for row in cursor.fetchall():
        entities.append({
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'degree': row['degree']
        })
    
    conn.close()
    
    return jsonify({'items': entities})


@entities_bp.route('/entities/<int:entity_id>/timeline', methods=['GET'])
def get_entity_timeline(entity_id):
    """
    GET /api/entities/:id/timeline
    
    Returns: { entity: {...}, articles: [{id, title, date, role_type}] }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get entity info
    cursor.execute("SELECT id, name, type FROM entities WHERE id = ?", (entity_id,))
    entity_row = cursor.fetchone()
    
    if not entity_row:
        conn.close()
        return jsonify({'ok': False, 'error': {'code': 'NOT_FOUND'}}), 404
    
    entity = {
        'id': entity_row['id'],
        'name': entity_row['name'],
        'type': entity_row['type']
    }
    
    # Get articles mentioning this entity
    cursor.execute("""
        SELECT a.id, a.title, a.date, er.role_type
        FROM articles a
        JOIN article_entities ae ON a.id = ae.article_id
        LEFT JOIN entity_roles er ON a.id = er.article_id AND ae.entity_id = er.entity_id
        WHERE ae.entity_id = ?
        ORDER BY a.date ASC
    """, (entity_id,))
    
    articles = []
    for row in cursor.fetchall():
        articles.append({
            'id': row['id'],
            'title': row['title'],
            'date': row['date'],
            'role_type': row['role_type'] or 'neutral'
        })
    
    conn.close()
    
    return jsonify({'entity': entity, 'articles': articles})


@entities_bp.route('/entities/<int:entity_id>/relationships', methods=['GET'])
def get_entity_relationships(entity_id):
    """
    GET /api/entities/:id/relationships
    
    Returns: { related_entities: [{entity_id, name, co_mention_count}] }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Find entities co-mentioned with this one
    cursor.execute("""
        SELECT e.id, e.name, COUNT(*) as co_mentions
        FROM entities e
        JOIN article_entities ae2 ON e.id = ae2.entity_id
        WHERE ae2.article_id IN (
            SELECT article_id FROM article_entities WHERE entity_id = ?
        )
        AND e.id != ?
        GROUP BY e.id, e.name
        ORDER BY co_mentions DESC
        LIMIT 50
    """, (entity_id, entity_id))
    
    related = []
    for row in cursor.fetchall():
        related.append({
            'entity_id': row['id'],
            'name': row['name'],
            'co_mention_count': row['co_mentions']
        })
    
    conn.close()
    
    return jsonify({'related_entities': related})
```

## Pipeline Integration

Update `backend/services/pipeline.py`:

```python
def step_ner(self, force_recompute=False):
    """Step 8: Named Entity Recognition."""
    logger.info("Step 8: Extracting named entities...")
    
    from backend.services.ner import NERService
    
    service = NERService()
    stats = service.extract_entities(force_recompute=force_recompute)
    
    if stats.get('articles_processed', 0) > 0:
        self.steps_completed.add(8)
    
    return stats

def step_entity_roles(self, force_recompute=False):
    """Step 8b: Entity role classification."""
    logger.info("Step 8b: Classifying entity roles...")
    
    from backend.services.ner import NERService
    
    service = NERService()
    stats = service.classify_entity_roles(force_recompute=force_recompute)
    
    return stats
```

## Frontend View

**File:** `static/js/views/entityTimeline.js`

```javascript
/**
 * Entity Timeline View
 */

export class EntityTimelineView {
    constructor(container) {
        this.container = container;
    }
    
    async load(entityId) {
        console.log('Loading Entity Timeline:', entityId);
        
        try {
            const response = await fetch(`/api/entities/${entityId}/timeline`);
            const data = await response.json();
            
            this.render(data);
        } catch (error) {
            console.error('Error loading entity timeline:', error);
        }
    }
    
    render(data) {
        const { entity, articles } = data;
        
        this.container.innerHTML = `
            <div style="padding: 2rem;">
                <h2>${entity.name} <span style="color: #999; font-size: 0.9rem;">(${entity.type})</span></h2>
                <p>Mentioned in ${articles.length} articles</p>
                
                <div style="margin-top: 2rem;">
                    <h3>Timeline</h3>
                    <div id="entity-timeline-chart" style="width: 100%; height: 400px;"></div>
                </div>
            </div>
        `;
        
        // TODO: Render timeline chart
        this.renderTimelineChart(articles);
    }
    
    renderTimelineChart(articles) {
        // TODO: Implement timeline visualization
        console.log('Articles:', articles);
    }
}
```

## Testing

**File:** `tests/unit/test_ner.py`

```python
"""
Tests for NER service
"""

import pytest
from backend.services.ner import NERService, ENTITY_STOPLIST


def test_stoplist_filtering():
    """Test entity stoplist filtering."""
    assert NERService()._is_stop_entity("United States", "GPE") == True
    assert NERService()._is_stop_entity("Washington", "GPE") == False


def test_role_classification():
    """Test entity role classification."""
    service = NERService()
    
    sentences = [
        "President Trump announced a new policy today.",
        "The announcement was made after months of planning."
    ]
    
    role, confidence = service._classify_role("", "Trump", sentences)
    assert role in ['protagonist', 'antagonist', 'subject', 'adjudicator', 'neutral']
    assert 0 <= confidence <= 1
```

## Next Steps

1. Run spaCy model download in setup
2. Test entity extraction on sample articles
3. Refine stoplist based on results
4. Improve role classification accuracy
5. Add entity disambiguation for common names
