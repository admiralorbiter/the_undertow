"""
Full-text search service using SQLite FTS5.
"""
from backend.db import get_db
from urllib.parse import quote


def search_articles(query, date_from='', date_to='', outlet='', limit=100, offset=0, count_only=False):
    """
    Search articles using FTS5.
    
    Args:
        query: Search query string
        date_from: Start date filter (YYYY-MM-DD)
        date_to: End date filter (YYYY-MM-DD)
        outlet: Outlet filter
        limit: Maximum results
        offset: Pagination offset
        count_only: If True, return only the count
    
    Returns:
        List of matching articles or count if count_only=True
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Build FTS5 query (escape special characters)
    # Simple approach: use phrase search for multi-word queries
    fts_query = query.replace('"', '""')  # Escape quotes
    if ' ' in fts_query:
        fts_query = f'"{fts_query}"'  # Phrase search
    
    # Build conditions (using fts alias)
    conditions = ["fts MATCH ?"]
    params = [fts_query]
    
    # Join with articles table for additional filters
    if date_from:
        conditions.append("a.date >= ?")
        params.append(date_from)
    
    if date_to:
        conditions.append("a.date <= ?")
        params.append(date_to)
    
    if outlet:
        conditions.append("a.outlet = ?")
        params.append(outlet)
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    if count_only:
        cursor.execute(f"""
            SELECT COUNT(DISTINCT a.id)
            FROM articles_fts fts
            JOIN articles a ON fts.rowid = a.id
            {where_clause}
        """, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # Get matching articles with ranking
    query_params = params + [limit, offset]
    cursor.execute(f"""
        SELECT a.id, a.title, a.summary, a.url, a.outlet, a.date, a.date_bin,
               bm25(fts) as rank
        FROM articles_fts fts
        JOIN articles a ON fts.rowid = a.id
        {where_clause}
        ORDER BY rank
        LIMIT ? OFFSET ?
    """, query_params)
    
    results = cursor.fetchall()
    conn.close()
    
    return results

