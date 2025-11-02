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

