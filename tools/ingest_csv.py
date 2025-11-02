#!/usr/bin/env python
"""
Simple CSV ingestion script.
Ingests the CSV file into the database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.ingest import ingest_csv
from backend.db import init_db

def main():
    # Initialize database schema
    init_db()
    
    # Ingest CSV
    csv_path = Path(__file__).parent.parent / 'data' / 'summarized_output.csv'
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    print(f"Ingesting CSV from: {csv_path}")
    print("This may take a moment...\n")
    
    try:
        stats = ingest_csv(csv_path, skip_duplicates=True)
        
        print("\n=== Ingestion Complete ===\n")
        print(f"Inserted: {stats['inserted']}")
        print(f"Skipped:  {stats['skipped']}")
        print(f"Errors:   {stats['errors']}")
        
        if stats['errors'] > 0:
            print(f"\n[WARNING] {stats['errors']} rows had errors and were skipped.")
            print("   Check your CSV for missing Title, URL, or invalid Date fields.")
        
        if stats['inserted'] == 0:
            print("\n[WARNING] No articles were inserted. Check if:")
            print("   1. CSV file has correct columns: Title, Date, URL, Summary")
            print("   2. Articles already exist in database (use --force to re-ingest)")
            sys.exit(1)
        
        print("\n[SUCCESS] CSV ingestion successful!")
        print("\nNext step: Run the pipeline:")
        print("   python tools/run_pipeline.py")
        
    except Exception as e:
        print(f"\n[ERROR] Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

