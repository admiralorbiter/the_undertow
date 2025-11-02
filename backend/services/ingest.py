"""
CSV ingestion service.
Parses CSV, normalizes data, and inserts into database.
"""
import csv
import sqlite3
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from backend.db import get_db
from backend.config import Config


def extract_outlet(url):
    """Extract outlet domain from URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return None


def normalize_date(date_str):
    """
    Normalize date string to ISO format (YYYY-MM-DD).
    
    Handles formats like:
    - 2/10/25 -> 2025-02-10
    - 02/11/2025 -> 2025-02-11
    - 2025-02-10 -> 2025-02-10
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Try common formats
    formats = [
        '%m/%d/%y',      # 2/10/25
        '%m/%d/%Y',     # 02/11/2025
        '%Y-%m-%d',     # 2025-02-10
        '%m-%d-%Y',     # 02-11-2025
        '%d/%m/%Y',     # 10/02/2025
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If year is 2-digit and result is in future, assume it's actually past
            if dt.year > 2100:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # If all parsing fails, return None
    print(f"Warning: Could not parse date: {date_str}")
    return None


def compute_date_bin(date_str):
    """
    Compute date bin (YYYY-MM) from ISO date string.
    """
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m')
    except ValueError:
        return None


def ingest_csv(csv_path, skip_duplicates=True):
    """
    Ingest articles from CSV file.
    
    Args:
        csv_path: Path to CSV file
        skip_duplicates: If True, skip articles with duplicate URLs
    
    Returns:
        dict with stats: {'inserted': int, 'skipped': int, 'errors': int}
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {'inserted': 0, 'skipped': 0, 'errors': 0}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    title = row.get('Title', '').strip()
                    summary = row.get('Summary', '').strip()
                    url = row.get('URL', '').strip()
                    date_str = row.get('Date', '').strip()
                    
                    # Skip rows with missing essential fields
                    if not title or not url:
                        stats['errors'] += 1
                        continue
                    
                    # Normalize data
                    date = normalize_date(date_str)
                    if not date:
                        stats['errors'] += 1
                        continue
                    
                    outlet = extract_outlet(url)
                    date_bin = compute_date_bin(date)
                    
                    # Check for duplicate URL
                    if skip_duplicates:
                        cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
                        if cursor.fetchone():
                            stats['skipped'] += 1
                            continue
                    
                    # Insert article
                    cursor.execute("""
                        INSERT INTO articles (title, summary, url, outlet, date, date_bin)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (title, summary, url, outlet, date, date_bin))
                    
                    stats['inserted'] += 1
                    
                except sqlite3.IntegrityError:
                    # Duplicate URL (if skip_duplicates=False)
                    stats['skipped'] += 1
                except Exception as e:
                    print(f"Error processing row: {e}")
                    stats['errors'] += 1
        
        conn.commit()
        print(f"Ingestion complete: {stats['inserted']} inserted, {stats['skipped']} skipped, {stats['errors']} errors")
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"CSV ingestion failed: {e}")
    finally:
        conn.close()
    
    return stats

