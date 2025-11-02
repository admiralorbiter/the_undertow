# Project: News Relationship Explorer

A small, local-first web app that ingests news articles (Title, Date, URL, Summary), discovers relationships (similarity, entities, topics, timelines), and surfaces them through interactive visualizations — without React.

---

## 1) Goals & Non‑Goals

**Goals**
- Transform a CSV of articles into a browsable knowledge map.
- Show relationships: similarity clusters, shared entities, topic trends over time.
- Provide explainability: *why* two things are linked (shared entities/terms, cosine similarity).
- Keep the stack lightweight: Flask + SQLite backend, non‑React JS frontend.

**Non‑Goals**
- Full blown web scraping/crawling at scale (out of scope for MVP).
- Heavy user management or multi‑tenant auth (start local-only / single user).
- Perfect NER/entity disambiguation (we aim for pragmatic extraction first).

---

## 2) Prioritized Roadmap (Phased)

**P0 – Foundations (Day 0)**
- Project scaffolding; environment; dependency pins.
- SQLite schema + migrations; seed from CSV.
- Basic API (articles list, search, filters by time/outlet).
- Full‑Text Search on title/summary via SQLite FTS5.

**P1 – MVP (Core Visual Insights)**
- Embeddings (MiniLM) + similarity graph build.
- UMAP 2D projection + *Galaxy View* (scatter with zoom + hover cards).
- Clustering (HDBSCAN; fallback k‑means) + auto‑labels (KeyBERT/YAKE).
- Time density chart (weekly/monthly counts; per cluster filter).
- Explain-why panel (shared entities/terms, cosine score).

**P2 – Relationship Deep‑Dive**
- NER (spaCy) for People/Orgs/Places.
- Entity co‑mention network (toggle types, filter by date/cluster).
- Storyline threading: near‑duplicate grouping within ±3 days.

**P3 – Advanced Views & UX**
- Sankey/Alluvial: topic flows over time.
- Outlet × Topic matrix (Marimekko‑style tile grid).
- Saved views + sharable filter URLs.

**P4 – Stretch (see §13)**
- Geo map (MapLibre/Leaflet) from place NER + geocoding.
- Stance/sentiment classifiers; bias slice.
- Alerting on surges; newsletter export.

Each phase should be shippable; phases are additive.

---

## 3) Data Inputs & Enrichment

**Given columns**: `Title, Date, URL, Summary`

**Derived fields**
- `outlet` (domain from URL)
- `date_bin` (week/month for aggregation)
- `keywords` (KeyBERT/YAKE on title+summary)
- `embedding` (MiniLM 384‑dim vector)
- `cluster_id` (from HDBSCAN/k‑means)
- `entities` (spaCy NER: PERSON, ORG, GPE/LOC)
- `similarity_edges` (pairs over threshold; store evidence)

**Notes**
- Date normalization to UTC midnight; store ISO‑8601.
- Dedup: exact hash of `Title|Summary|outlet|date` and near‑dup via high similarity.

---

## 4) System Architecture

```
+-------------------+        +-----------------+        +-------------------+
|   Frontend (JS)   |  <---> | Flask API (REST)|  <-->  | SQLite + FTS5     |
|  ECharts, D3,     |        |  /json endpoints |        | Articles, Entities |
|  Cytoscape, HTMX  |        |                  |        | Graph tables       |
+-------------------+        +-----------------+        +-------------------+
                                  |                         |
                                  |                         +--> FAISS (vector index file)
                                  +--> Python NLP (spaCy, sentence-transformers, KeyBERT)
```

**Why this shape:** computation (embeddings, clustering) lives in Python; storage in SQLite; frontend requests pre‑baked datasets for fast rendering.

---

## 5) Storage Schema (SQLite)

**articles**
- `id` INTEGER PK
- `title` TEXT
- `summary` TEXT
- `url` TEXT UNIQUE
- `outlet` TEXT
- `date` TEXT (ISO date)
- `date_bin` TEXT (e.g., `2025‑10`)
- `cluster_id` INTEGER NULL

**articles_fts (virtual FTS5)**
- `title`, `summary`, `content='articles', content_rowid='id'`

**embeddings**
- `article_id` INTEGER PK FK → articles.id
- `vec` BLOB (float32[384])

**entities**
- `id` INTEGER PK
- `name` TEXT
- `type` TEXT CHECK(type IN ('PERSON','ORG','GPE','LOC','OTHER'))

**article_entities**
- `article_id` INTEGER FK
- `entity_id` INTEGER FK
- `weight` REAL (e.g., count/score)
- PK(article_id, entity_id)

**clusters**
- `id` INTEGER PK
- `label` TEXT (auto‑label)
- `size` INTEGER
- `score` REAL (confidence/cohesion)

**similarities**
- `src_id` INTEGER FK → articles.id
- `dst_id` INTEGER FK → articles.id
- `cosine` REAL
- `shared_entities` TEXT (JSON array of entity_ids)
- `shared_terms` TEXT (JSON of top n‑grams)
- PK(src_id, dst_id)

**indexes**
- `CREATE INDEX idx_articles_date ON articles(date);`
- `CREATE INDEX idx_articles_outlet ON articles(outlet);`
- `CREATE INDEX idx_entities_name ON entities(name);`

**Vector search**
- FAISS index saved to `data/faiss.index` + table `vector_meta(version, dim, count)`.

---

## 6) API Design (REST JSON)

**GET /api/articles**
- Query: `q` (full‑text), `from`, `to`, `outlet`, `cluster_id`, `entity`, `limit`, `offset`.
- Returns: `{ items: [ {id,title,date,url,outlet,summary,cluster_id} ], total }`

**GET /api/clusters**
- Returns cluster list: `{ clusters: [{id,label,size,score}], stats:{...} }`

**GET /api/cluster/:id/articles**
- Returns articles in a cluster.

**GET /api/umap**
- Returns 2D positions: `{ points: [{id,x,y,cluster_id}], meta:{model:'MiniLM', umap:{n_neighbors, min_dist}} }`

**GET /api/similar/:id**
- Top‑k similar: `{ items: [{id, cosine, why:{shared_entities,shared_terms}}] }`

**GET /api/entities**
- Query: `type`, `q`, `min_degree`.
- Returns: `{ items: [{id,name,type,degree}] }`

**GET /api/graph/entities**
- Returns co‑mention network: `{ nodes:[{id,label,type}], edges:[{s,t,w,why}] }`

**GET /api/timeline**
- Returns counts over time: `{ bins:[{date,count,by_cluster:{cluster_id: n}}] }`

**POST /api/ingest/csv**
- Multipart upload or path; triggers pipeline.
- Returns job id and summary.

**GET /api/storylines**
- Returns near‑duplicate groups: `{ threads:[{id, article_ids, head_id, span_days}] }`

**Errors**
- Consistent envelope: `{ ok:false, error:{code,message,details} }` with 4xx/5xx.

---

## 7) Frontend Architecture (Non‑React)

**Principles**
- Lightweight, modular, progressive enhancement.
- Plain TypeScript (compiled) + ES Modules.
- Components as Web Components (Lit optional) or simple classes targeting DOM roots.

**Libraries**
- **ECharts** for scatter (UMAP), line/area timelines, Sankey, heatmaps.
- **Cytoscape.js** for entity networks.
- **HTMX** for small server‑rendered fragments (lists/details) without a SPA.
- **Luxon** for date handling.
- **Micromodal** (tiny) for modals; or custom.
- **Pico.css** (or vanilla CSS) for styling.

**Layout**
- Left: Filters (search, time range, outlet, cluster/entity chips).
- Center: Main viz (Galaxy/Timeline/Network tabs).
- Right: Details panel (article info, "why related" evidence).

**Key Views**
- **Galaxy View**: UMAP scatter (ECharts) with zoom/brush; color by cluster; hover = title+summary; click selects article → details panel.
- **Timeline**: stacked area by cluster; brushing updates other views.
- **Entity Graph**: Cytoscape force layout; filter by type/date; click node shows linked articles; edge hover shows co‑mention counts.

**Interactions**
- Cross‑filtering: brushing timeline filters galaxy and graph.
- Selection state in URL (query params) for shareable state.
- Keyboard shortcuts: `/` focus search, `Esc` clear selection.

---

## 8) NLP & Analytics Pipeline

**1. Ingest**
- Read CSV, normalize `date`, parse `outlet` from URL, store rows.
- Upsert by URL; skip exact dups.

**2. FTS Index**
- Populate FTS5 shadow table.

**3. Embeddings**
- Model: `sentence-transformers/all-MiniLM-L6-v2` (384‑dim).
- Text: `title + " \n " + summary`.
- Persist float32 vectors; build FAISS (IndexFlatIP) for cosine similarity.

**4. Similarity Graph**
- For each article, get top‑k (e.g., 20) neighbors above `cosine ≥ 0.6`.
- Compute shared entities/terms (later steps) as `why` evidence.

**5. Clustering**
- HDBSCAN (metric=cosine, min_cluster_size≈8). Fallback: k‑means with silhouette sweep to choose k.

**6. UMAP**
- 2D projection for front‑end; store only 2D coords (x,y) per article.

**7. Keyword/Labeling**
- KeyBERT/YAKE per cluster; top 3 labels → `clusters.label`.

**8. NER**
- spaCy `en_core_web_sm` (lightweight) on title+summary. Extract PERSON/ORG/GPE/LOC; store counts per article.

**9. Storylines (near‑dup)**
- Union‑Find on edges with `cosine ≥ 0.85` AND `|date_i - date_j| ≤ 3 days`.

**Batching**
- Run steps 3–9 as an idempotent pipeline. On ingest, enqueue job; otherwise allow manual rebuild.

---

## 9) Explainability

For any link (article→article or node→node), show:
- **Cosine similarity** (0–1)
- **Shared entities** (with types)
- **Shared top n‑grams** (TF‑IDF intersection)
- **Date proximity** (days apart)
- **Outlet overlap** (same/different)

Keep a small JSON blob (`why`) on edges for fast UI.

---

## 10) Security, Privacy, and Performance

- **Local‑first**: default run on localhost; CORS disabled unless configured.
- **Input sanitation**: escape titles/summaries; no raw HTML.
- **Rate limiting** (Flask‑Limiter) on heavy endpoints.
- **Caching**:
  - API responses with `ETag` on static datasets (`/api/umap`, `/api/clusters`).
  - In‑process LRU for common queries; optional file cache for computed artifacts.
- **Perf**:
  - Persist UMAP/cluster results; avoid recomputation on every load.
  - FAISS top‑k instead of O(n²) similarity.
  - Chunk NER/KeyBERT by batch size; reuse spaCy nlp object.

---

## 11) Testing & QA

**Backend**
- Unit: date parsing, outlet extraction, TF‑IDF, NER wrapper, embeddings adapter.
- Integration: /api/* endpoints with seeded SQLite.
- Determinism: snapshot tests for cluster labeling on fixed seed.

**Frontend**
- Cypress smoke tests for interaction flows (filter, brush, select, deep‑link).
- Visual regression on key charts (optional Percy/Chromatic alternatives).

---

## 12) Deployment & Ops

- **Local dev**: `pipenv` or `uv` for Python; Vite for bundling TS.
- **Packaging**: Dockerfile with model cache volume (`/models`).
- **Config**: `.env` (paths, thresholds, ports). Example knobs: `SIM_THRESHOLD`, `CLUSTER_MIN_SIZE`, `KNN_K`.
- **Artifacts**: persist `faiss.index`, `umap.json`, `clusters.json`, `graph.json` under `/data`.

---

## 13) Stretch Goals (Extensions)

- **Geo view**: geocode GPE entities (Nominatim) → MapLibre map; cluster pins.
- **Stance/Bias**: light classifier per topic; outlet comparison.
- **Summarize clusters**: create abstractive summary of each cluster (e.g., Pegasus‑small or TextRank extractive to start).
- **Alerts**: weekly surge detector → email/markdown digest.
- **Quote extraction**: identify quotes + speakers; build a "quote board" UI.
- **Wikidata linking**: disambiguate entities; enrich with descriptions/logos.
- **Exports**: CSV/PNG of charts; newsletter builder for top stories.

---

## 14) Acceptance Criteria (MVP)

- Upload CSV → ingest succeeds; dedups handled.
- `/api/umap` returns ≥ N points with cluster_id for ≥ 80% of articles.
- Galaxy view renders in < 2s on 2k points; hover + click work.
- Timeline brush filters galaxy points live.
- For a selected article, `/api/similar/:id` returns ≥ 5 items with cosine + shared entities/terms.
- Entity network displays with degree filter; clicking a node lists linked articles.

---

## 15) Example Payloads

**/api/umap**
```json
{
  "points": [
    {"id": 123, "x": -3.12, "y": 1.04, "cluster_id": 7},
    {"id": 124, "x": -2.87, "y": 0.92, "cluster_id": 7}
  ],
  "meta": {"model":"MiniLM-L6-v2", "umap": {"n_neighbors": 15, "min_dist": 0.1}}
}
```

**/api/graph/entities**
```json
{
  "nodes": [
    {"id": "e1", "label": "OpenAI", "type": "ORG"},
    {"id": "e2", "label": "Kansas City", "type": "GPE"}
  ],
  "edges": [
    {"s": "e1", "t": "e2", "w": 12, "why": {"articles": [101, 203, 417]}}
  ]
}
```

---

## 16) File/Folder Layout

```
repo/
  backend/
    app.py                 # Flask entry; routes
    api/
      articles.py
      clusters.py
      graph.py
      search.py
    services/
      ingest.py
      embeddings.py
      clustering.py
      ner.py
      labeling.py
      umap.py
    models/
      db.py                # SQLAlchemy setup
      schema.sql           # migrations
    data/
      faiss.index
      umap.json
      clusters.json
    tests/
  frontend/
    index.html
    assets/
      styles.css
    src/
      main.ts              # boot + router
      api.ts               # fetch helpers
      views/
        galaxy.ts
        timeline.ts
        entityGraph.ts
        list.ts
      components/
        detailsPanel.ts
        filterPanel.ts
    vite.config.ts
```

---

## 17) Implementation Notes & Defaults

- **Similarity threshold**: start at 0.60; expose via `.env`.
- **Clustering**: HDBSCAN `min_cluster_size=8`, `min_samples=1`; seed UMAP for stability.
- **UMAP**: `n_neighbors=15`, `min_dist=0.1`, `metric='cosine'`.
- **KeyBERT**: top 10 per cluster; keep top 3 as labels.
- **Entity filtering**: drop stop‑entities (`United States`, `Monday`, etc.).
- **FTS5**: `tokenize = porter unicode61`.

---

## 18) Open Questions (to validate while building)

- Is offline use a hard requirement (i.e., model downloads pre‑baked)?
- Any specific outlets/entities to whitelist or blacklist?
- Preferred chart palettes / accessibility constraints (high contrast)?
- Export formats needed (CSV/PNG/PDF)?

---

## 19) Quick Setup Script (outline)

1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python -m spacy download en_core_web_sm`
4. `python tools/ingest_csv.py data/summarized_output.csv`
5. `python tools/build_indexes.py` (embeddings → FAISS; UMAP; clusters)
6. `vite dev` (serve frontend) + `flask --app backend/app run`

---

This spec is intentionally practical and incremental so we can ship value quickly (Galaxy + Timeline), then deepen (Entity network, Storylines, Alluvial) without re‑architecting.

