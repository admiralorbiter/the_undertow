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

