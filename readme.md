# News Relationship Explorer

A local-first web application that ingests news articles, discovers relationships (similarity, entities, topics, timelines), and surfaces them through interactive visualizations.

## Overview

This project transforms a CSV of news articles into a browsable knowledge map. It uses Flask + SQLite for the backend and vanilla JavaScript (no React) for the frontend. See `tech+design.md` for the complete technical specification.

## Features

**P0 - Foundations:**
- ✅ CSV ingestion with automatic deduplication
- ✅ SQLite database with FTS5 full-text search
- ✅ Article browsing with search and filters
- ✅ Outlet and date filtering
- ✅ Responsive web interface

**P1 - Core Visual Insights:**
- ✅ Embeddings (MiniLM-L6-v2) + similarity graph
- ✅ UMAP Galaxy View (similarity scatter plot)
- ✅ Clustering (HDBSCAN) and auto-labeling
- ✅ Timeline analysis
- ✅ Relationship explainability

**P2 - Narrative Intelligence:**
- ✅ Named Entity Recognition (spaCy) - PEOPLE, ORG, GPE extraction
- ✅ Multi-tier storyline detection (near-duplicates, continuations, related)
- ✅ Momentum scoring (active vs. dormant vs. concluded)
- 🔜 Entity role classification
- 🔜 Causal chain discovery

**P3 - Monitoring & Alerting:**
- ✅ State-of-the-World Dashboard (active storylines, heatmaps, key actors)
- ✅ Anomaly Detection (topic surges, story reactivations, new actor emergence)
- ✅ Alert Management (acknowledge, filter, severity classification)

**Coming Soon:**
- Entity network visualization
- Causal chain discovery

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

5. **Download spaCy language model**

   ```bash
   python -m spacy download en_core_web_sm
   ```

   Note: This downloads the English language model for Named Entity Recognition.

6. **Ingest your CSV data**

   The app will create the database on first run. To ingest your CSV file:

   ```bash
   # Using Python directly
   python -c "from backend.services.ingest import ingest_csv; ingest_csv('data/summarized_output.csv')"
   ```

   Or use the API endpoint after starting the server (see below).

7. **Run the ML pipeline**

   After ingesting articles, run the pipeline to generate embeddings, clusters, and visualizations:

   ```bash
   # Run all pipeline steps (embeddings → similarity → clustering → UMAP → labeling → NER → storylines → monitoring)
   python tools/run_pipeline.py

   # Run from a specific step
   python tools/run_pipeline.py --step 4

   # Run P2 features (NER + storylines)
   python tools/run_pipeline.py --step 8

   # Run P3 monitoring (detections + alerts)
   python tools/run_pipeline.py --step 10

   # Force recompute everything
   python tools/run_pipeline.py --force

   # Check pipeline status
   python tools/run_pipeline.py --status
   ```

   Note: The first run will download ML models (sentence-transformers, spaCy) which may take a few minutes.

8. **Run the application**

   ```bash
   python app.py
   ```

   The server will start on `http://127.0.0.1:5000`

9. **Open in your browser**

   Navigate to `http://localhost:5000` to see the interface.
   
   - Switch between **List**, **Galaxy**, **Timeline**, **Dashboard**, and **Alerts** views
   - Click articles in the Galaxy view to see similarity relationships
   - View the timeline to see article distribution over time
   - Check the Dashboard for state-of-the-world summary
   - View Alerts to see anomaly detections (surges, reactivations, new actors)
   - Check the details panel for explain-why information about similar articles

### Ingest CSV via API

After starting the server, you can ingest CSV files via the API:

```bash
curl -X POST "http://localhost:5000/api/ingest/csv?path=summarized_output.csv"
```

Or use any HTTP client to POST to `/api/ingest/csv?path=<your-file.csv>`

### GET /api/entities

List entities with filters.

**Query Parameters:**
- `type` - Filter by entity type (PERSON, ORG, GPE, LOC, MISC)
- `q` - Search entities by name
- `min_degree` - Minimum number of articles mentioning entity

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Elon Musk",
      "type": "PERSON",
      "degree": 45
    }
  ]
}
```

### GET /api/entities/:id/timeline

Get timeline of articles mentioning an entity.

**Response:**
```json
{
  "entity": {"id": 1, "name": "Elon Musk", "type": "PERSON"},
  "articles": [
    {"id": 123, "title": "...", "date": "2025-02-10", "role_type": "protagonist"}
  ]
}
```

### GET /api/entities/:id/relationships

Get entities frequently co-mentioned with this entity.

**Response:**
```json
{
  "related_entities": [
    {"entity_id": 2, "name": "Tesla", "co_mention_count": 12}
  ]
}
```

### GET /api/storylines

List storylines with filters.

**Query Parameters:**
- `status` - Filter by status (active, dormant, concluded)
- `min_momentum` - Minimum momentum score
- `from_date`, `to_date` - Date range

**Response:**
```json
{
  "storylines": [
    {
      "id": 1,
      "label": "Trump spending freeze court challenges",
      "status": "active",
      "momentum_score": 1.5,
      "article_count": 8,
      "first_date": "2025-02-10",
      "last_date": "2025-02-15"
    }
  ]
}
```

### GET /api/storyline/:id/articles

Get articles in a storyline, ordered chronologically.

**Response:**
```json
{
  "storyline": {
    "id": 1,
    "label": "...",
    "status": "active",
    "momentum_score": 1.5
  },
  "articles": [
    {
      "id": 123,
      "title": "...",
      "date": "2025-02-10",
      "tier": "tier1",
      "sequence_order": 0
    }
  ]
}
```

### GET /api/dashboard/summary

Get aggregated dashboard data showing system state.

**Query Parameters:**
- `days_back` - Number of days to include (default: 30, range: 7-365)

**Response:**
```json
{
  "stats": {
    "total_articles": 581,
    "active_storylines_count": 5,
    "dormant_storylines_count": 56,
    "total_entities": 1374,
    "new_articles_7d": 38
  },
  "active_storylines": [
    {
      "id": 1,
      "label": "...",
      "status": "active",
      "momentum_score": 3.0,
      "article_count": 3,
      "first_date": "2025-10-27",
      "last_date": "2025-10-28"
    }
  ],
  "temporal_heatmap": [
    {"date": "2025-10-27", "count": 9}
  ],
  "key_actors": [
    {
      "entity_id": 1,
      "name": "Trump",
      "type": "PERSON",
      "mentions_7d": 19
    }
  ],
  "cluster_evolution": [
    {
      "date": "2025-10-31",
      "cluster_sizes": {"0.0": 1, "2.0": 2}
    }
  ],
  "recent_alerts": []
}
```

### GET /api/alerts

List alerts with filters.

**Query Parameters:**
- `limit` - Max results (default: 50, max: 200)
- `alert_type` - Filter by type (topic_surge, story_reactivation, new_actor, divergence)
- `severity` - Filter by severity (low, medium, high)
- `since` - ISO timestamp to filter from

**Response:**
```json
{
  "alerts": [
    {
      "id": 1,
      "alert_type": "topic_surge",
      "entity_json": "{\"cluster_id\": 3, \"current_count\": 15, \"previous_count\": 8}",
      "triggered_at": "2025-10-28T12:00:00",
      "description": "Cluster 3: 15 articles in last 7 days vs 8 in previous week (1.9x growth)",
      "severity": "medium",
      "acknowledged": false
    }
  ]
}
```

### POST /api/alerts/:id/acknowledge

Mark alert as acknowledged.

**Response:**
```json
{
  "success": true,
  "acknowledged": 1
}
```

### POST /api/monitoring/run

Trigger detection run manually.

**Response:**
```json
{
  "alerts_created": 5,
  "surges": 2,
  "reactivations": 1,
  "new_actors": 2
}
```

### GET /api/monitoring/stats

Get monitoring statistics.

**Response:**
```json
{
  "total_alerts": 42,
  "unacknowledged_alerts": 15,
  "recent_alerts_24h": 3
}
```

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

