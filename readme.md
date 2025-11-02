# News Relationship Explorer

A local-first web application that ingests news articles, discovers relationships (similarity, entities, topics, timelines), and surfaces them through interactive visualizations.

## Overview

This project transforms a CSV of news articles into a browsable knowledge map. It uses Flask + SQLite for the backend and vanilla JavaScript (no React) for the frontend. See `tech+design.md` for the complete technical specification.

## Features (Current - P0)

- ✅ CSV ingestion with automatic deduplication
- ✅ SQLite database with FTS5 full-text search
- ✅ Article browsing with search and filters
- ✅ Outlet and date filtering
- ✅ Responsive web interface

## Coming Soon (P1+)

- UMAP Galaxy View (similarity scatter plot)
- Clustering and auto-labeling
- Entity network visualization
- Timeline analysis
- Relationship explainability

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the project directory**

   ```bash
   cd the_undertow
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**

   On Windows:
   ```bash
   .venv\Scripts\activate
   ```

   On macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Ingest your CSV data**

   The app will create the database on first run. To ingest your CSV file:

   ```bash
   # Using Python directly
   python -c "from backend.services.ingest import ingest_csv; ingest_csv('data/summarized_output.csv')"
   ```

   Or use the API endpoint after starting the server (see below).

6. **Run the ML pipeline (P1 features)**

   After ingesting articles, run the pipeline to generate embeddings, clusters, and visualizations:

   ```bash
   # Run all pipeline steps (embeddings → similarity → clustering → UMAP → labeling)
   python tools/run_pipeline.py

   # Run from a specific step
   python tools/run_pipeline.py --step 4

   # Force recompute everything
   python tools/run_pipeline.py --force

   # Check pipeline status
   python tools/run_pipeline.py --status
   ```

   Note: The first run will download ML models (sentence-transformers, etc.) which may take a few minutes.

7. **Run the application**

   ```bash
   python app.py
   ```

   The server will start on `http://127.0.0.1:5000`

8. **Open in your browser**

   Navigate to `http://localhost:5000` to see the interface.
   
   - Switch between **List**, **Galaxy**, and **Timeline** views
   - Click articles in the Galaxy view to see similarity relationships
   - View the timeline to see article distribution over time
   - Check the details panel for explain-why information about similar articles

### Ingest CSV via API

After starting the server, you can ingest CSV files via the API:

```bash
curl -X POST "http://localhost:5000/api/ingest/csv?path=summarized_output.csv"
```

Or use any HTTP client to POST to `/api/ingest/csv?path=<your-file.csv>`

## Project Structure

```
the_undertow/
├── app.py                    # Main Flask entry point
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── readme.md                # This file
├── tech+design.md          # Complete technical specification
│
├── backend/                 # Backend Python code
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── db.py               # Database schema and connection
│   ├── api/                # API endpoints
│   │   ├── __init__.py
│   │   └── articles.py     # Article endpoints
│   └── services/           # Business logic
│       ├── __init__.py
│       ├── ingest.py       # CSV ingestion service
│       └── search.py       # FTS5 search wrapper
│
├── static/                  # Frontend files
│   ├── index.html          # Main HTML page
│   ├── css/
│   │   └── styles.css      # Styling
│   └── js/
│       ├── main.js         # App initialization
│       ├── api.js          # API client
│       └── views/          # View components
│           ├── list.js     # List view
│           ├── galaxy.js   # Galaxy view (placeholder)
│           └── timeline.js # Timeline view (placeholder)
│
├── data/                    # Data directory
│   └── summarized_output.csv  # Input CSV
│
└── instance/                # Instance-specific files (created at runtime)
    └── app.db              # SQLite database
```

## API Endpoints

### GET /api/articles

Get articles with optional filters.

**Query Parameters:**
- `q` - Full-text search query
- `from` - Start date (YYYY-MM-DD)
- `to` - End date (YYYY-MM-DD)
- `outlet` - Filter by outlet domain
- `limit` - Max results (default: 100, max: 1000)
- `offset` - Pagination offset (default: 0)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Article Title",
      "summary": "Article summary...",
      "url": "https://...",
      "outlet": "example.com",
      "date": "2025-02-10",
      "date_bin": "2025-02"
    }
  ],
  "total": 1234
}
```

### POST /api/ingest/csv

Ingest articles from a CSV file.

**Query Parameters:**
- `path` - Path to CSV file (relative to `data/` folder or absolute)

**Response:**
```json
{
  "ok": true,
  "stats": {
    "inserted": 100,
    "skipped": 5,
    "errors": 0
  }
}
```

## Configuration

Create a `.env` file in the root directory to customize settings:

```env
SECRET_KEY=your-secret-key-here
PORT=5000
DATABASE_PATH=instance/app.db
DATA_DIR=data
```

If no `.env` file exists, sensible defaults will be used.

## Development

### Running in Debug Mode

The app runs in debug mode by default when using `python app.py`. This enables:
- Auto-reload on code changes
- Detailed error messages
- Flask debug toolbar (if installed)

### Adding New Features

1. **API Endpoints**: Add new blueprints in `backend/api/`
2. **Services**: Add business logic in `backend/services/`
3. **Frontend Views**: Add new views in `static/js/views/`

See `tech+design.md` for the full roadmap and architecture details.

## Troubleshooting

### Database Errors

If you encounter database errors, try deleting `instance/app.db` and restarting the app to recreate the schema.

### Port Already in Use

If port 5000 is already in use, change it in `.env` or modify `app.py`:

```python
app.run(debug=True, host='127.0.0.1', port=5001)  # Use different port
```

### CSV Ingestion Issues

- Ensure your CSV has columns: `Title`, `Date`, `URL`, `Summary`
- Check that date formats are parseable (supports MM/DD/YY, YYYY-MM-DD, etc.)
- Check the console for detailed error messages

## License

See repository license file.

## Next Steps

After setting up, refer to `tech+design.md` for:
- Roadmap (P0-P4 phases)
- Planned features (embeddings, clustering, UMAP, NER)
- API design details
- Frontend architecture plans

