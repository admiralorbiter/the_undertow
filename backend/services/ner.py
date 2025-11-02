"""
Named Entity Recognition Service

Extracts entities from articles, tracks mentions, and classifies roles.
"""

import logging
import re
import spacy
from typing import List, Tuple
from backend.db import get_db

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
        1. Load articles without entities (or all if force)
        2. Run spaCy NER on title + summary
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

