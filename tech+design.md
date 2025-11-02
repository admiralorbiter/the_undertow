# Project: News Relationship Explorer → Narrative Intelligence System

A local-first web app that ingests news articles (Title, Date, URL, Summary), discovers relationships and **tracks narrative evolution** over time. Transforms collections of articles into a navigable intelligence system for understanding how stories develop, connect, and impact real-world events — without React.

---

## 1) Goals & Non‑Goals

**Goals**
- Transform a CSV of articles into a browsable knowledge map.
- **Track narrative evolution**: how individual stories develop, branch, and connect over time.
- **Discover causal chains**: identify Event A → Event B → Event C sequences with evidence.
- **Monitor the "state of the world"**: detect topic surges, dormant story reactivation, emerging patterns.
- Provide explainability: *why* two things are linked (shared entities/terms, cosine similarity, temporal proximity).
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

**P2 – Narrative Intelligence (Current Phase)**
- NER (spaCy) for People/Orgs/Places with entity timeline tracking.
- **Story Arc Detection**: Multi-tier storyline threading (near-duplicates, continuations, related developments).
- **Causal Chain Discovery**: Identify Event A → B → C sequences using temporal ordering, similarity, and entity overlap.
- Entity role tracking (protagonist/antagonist/subject/adjudicator).

**P3 – Monitoring & Alerting**
- **State-of-the-World Dashboard**: Active storylines, surge alerts, temporal heatmap, key actors.
- Anomaly/surge detection (topic surges, dormant story reactivation, new actor emergence).
- Cross-domain connection discovery (bridge articles, semantic paths between clusters).

**P4 – Prediction & Forecasting (Stretch)**
- Narrative continuation prediction (likely next developments based on historical patterns).
- Event impact estimation (potential story reach/scaling).
- Temporal forecasting (volume and topic trends in coming days/weeks).
- Sentiment tracking within storylines over time.

Each phase should be shippable; phases are additive.

**What Changed from Original Plan:**
- Deprioritized: entity co-mention networks (replaced by timeline-based tracking), outlet matrices, geo maps, saved views.
- New focus: narrative evolution, causal chains, real-time monitoring, predictive insights.

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
- `storyline_id` (which narrative thread this article belongs to)
- `event_type` (Executive Action, Court Ruling, Legislative, Protest, Statement, etc.)
- `sentiment` (positive/negative/neutral - optional for P4)

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
- `tier` TEXT CHECK(tier IN ('near_duplicate','continuation','related'))
- PK(src_id, dst_id)

**storylines**
- `id` INTEGER PK
- `label` TEXT (auto-generated storyline name)
- `status` TEXT CHECK(status IN ('active','dormant','concluded'))
- `momentum_score` REAL (article frequency weighted by recency)
- `first_date` TEXT (ISO date)
- `last_date` TEXT (ISO date)

**storyline_articles**
- `storyline_id` INTEGER FK → storylines.id
- `article_id` INTEGER FK → articles.id
- `tier` TEXT CHECK(tier IN ('tier1','tier2','tier3'))
- `sequence_order` INTEGER (chronological order within storyline)
- PK(storyline_id, article_id)

**causal_chains**
- `id` INTEGER PK
- `articles_json` TEXT (JSON array of article_ids in order)
- `chain_type` TEXT (Policy Chain, Actor Chain, Institutional Chain)
- `strength_score` REAL (aggregate confidence)
- `start_date` TEXT (ISO date)
- `end_date` TEXT (ISO date)

**entity_roles**
- `entity_id` INTEGER FK → entities.id
- `article_id` INTEGER FK → articles.id
- `role_type` TEXT CHECK(role_type IN ('protagonist','antagonist','subject','adjudicator','neutral'))
- `confidence` REAL
- PK(entity_id, article_id)

**alerts**
- `id` INTEGER PK
- `alert_type` TEXT CHECK(alert_type IN ('topic_surge','story_reactivation','new_actor','divergence'))
- `entity_json` TEXT (JSON object describing alert context)
- `triggered_at` TEXT (ISO timestamp)
- `description` TEXT
- `severity` TEXT CHECK(severity IN ('low','medium','high'))

**indexes**
- `CREATE INDEX idx_articles_date ON articles(date);`
- `CREATE INDEX idx_articles_outlet ON articles(outlet);`
- `CREATE INDEX idx_articles_storyline ON articles(storyline_id);`
- `CREATE INDEX idx_entities_name ON entities(name);`
- `CREATE INDEX idx_storyline_articles_order ON storyline_articles(storyline_id, sequence_order);`
- `CREATE INDEX idx_causal_chains_dates ON causal_chains(start_date, end_date);`
- `CREATE INDEX idx_alerts_triggered ON alerts(triggered_at DESC);`

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
- Query: `status`, `min_momentum`, `from_date`, `to_date`
- Returns storyline list: `{ storylines:[{id, label, status, momentum_score, article_count, first_date, last_date}] }`

**GET /api/storyline/:id/articles**
- Returns articles in a storyline: `{ storyline: {...}, articles:[{id, title, date, tier, sequence_order}] }`

**GET /api/storyline/:id/evolution**
- Returns evolution timeline: `{ nodes:[{article_id, date, tier}], edges:[{from, to, type}] }`

**GET /api/chains**
- Query: `chain_type`, `min_strength`
- Returns causal chains: `{ chains:[{id, articles, chain_type, strength_score, start_date, end_date}] }`

**GET /api/article/:id/upstream**
- Returns causal predecessors: `{ articles:[{id, title, date, relationship_type}] }`

**GET /api/article/:id/downstream**
- Returns causal successors: `{ articles:[{id, title, date, relationship_type}] }`

**GET /api/entities/:id/timeline**
- Returns entity mentions over time: `{ entity: {...}, articles:[{id, title, date, role_type}] }`

**GET /api/entities/:id/relationships**
- Returns entity co-mention relationships: `{ related_entities:[{entity_id, name, co_mention_count, relationship_type}] }`

**GET /api/alerts**
- Query: `severity`, `alert_type`, `since` (ISO timestamp)
- Returns recent alerts: `{ alerts:[{id, alert_type, description, severity, triggered_at, entity_json}] }`

**GET /api/monitoring/stats**
- Returns monitoring statistics: `{ active_storylines: int, dormant_storylines: int, recent_alerts: int, new_articles_7d: int, topics_surging: [...], top_entities: [...] }`

**GET /api/dashboard/summary**
- Returns state-of-the-world summary: `{ active_storylines:[...], recent_alerts:[...], temporal_heatmap:[...], key_actors:[...], cluster_evolution:[...] }`

**GET /api/clusters/bridges**
- Returns articles bridging multiple clusters: `{ bridges:[{article_id, clusters:[...], bridge_strength}] }`

**GET /api/clusters/cooccurrence**
- Returns cluster co-occurrence matrix: `{ matrix:[[cluster_a, cluster_b, count], ...] }`

**GET /api/path/:cluster_a/:cluster_b**
- Returns semantic path between clusters: `{ path:[{article_id, title, date}], intermediate_clusters:[...] }`

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
- **Storylines View**: River/Sankey-style narrative flow (timeline X-axis, storylines as flowing threads); click to expand thread; color intensity = activity.
- **Causal Chains View**: Node-link graph showing Event A → B → C sequences; temporal flow; highlight chain types.
- **Dashboard View**: State-of-the-world summary - active storylines, alerts, temporal heatmap, key actors, cluster evolution.
- **Entity Timeline**: Horizontal timeline for selected entity showing all mentions, role changes, activity peaks.

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
- Entity role classification: protagonist/antagonist/subject/adjudicator based on verb proximity and sentence structure.

**9. Storylines (Multi‑Tier)**
- Tier 1 (Near-duplicates): Union‑Find on edges with `cosine ≥ 0.85` AND `|date_i - date_j| ≤ 3 days`.
- Tier 2 (Continuations): `0.65 ≤ cosine < 0.85` AND `|date_i - date_j| ≤ 7 days`.
- Tier 3 (Related): `0.50 ≤ cosine < 0.65` with shared key entities.
- Momentum scoring: article frequency weighted by recency.

**10. Causal Chain Detection**
- Identify event sequences: temporal ordering + semantic continuity (0.45 ≤ cosine ≤ 0.70) + shared entities + causal language patterns.
- Chain types: Policy Chain, Actor Chain, Institutional Chain.
- Strength scoring: temporal proximity + similarity + entity overlap + causal language presence.

**11. Monitoring & Anomaly Detection**
- Topic surge detection: cluster growth rate monitoring, alert on >X% week-over-week.
- Dormant story reactivation: track storylines quiet >14 days, alert on new articles.
- New actor emergence: entities frequent in recent window but absent historically.
- Narrative divergence: detect contradictory patterns in similar stories.

**Batching**
- Run steps 3–11 as an idempotent pipeline. On ingest, enqueue job; otherwise allow manual rebuild.
- Monitoring (step 11) can run as background job after new articles ingested or on-demand.

---

## 9) Explainability

For any link (article→article or node→node), show:
- **Cosine similarity** (0–1)
- **Shared entities** (with types and roles)
- **Shared top n‑grams** (TF‑IDF intersection)
- **Date proximity** (days apart)
- **Outlet overlap** (same/different)
- **Relationship tier** (near-duplicate/continuation/related)
- **Causal evidence** (if applicable: detected causal language, chain membership)

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

- **Prediction engine**: narrative continuation prediction, event impact estimation, temporal volume forecasting.
- **Sentiment tracking**: sentiment shifts within storylines over time.
- **Outlet classification**: categorize outlets (mainstream/alternative, partisan lean) to identify narrative bias.
- **Event type tagging**: auto-classify articles as Executive Action, Court Ruling, Legislative, Protest, Statement, etc.
- **Citation network**: track article references/citations to build influence graph.
- **Summarize clusters**: create abstractive summary of each cluster (e.g., Pegasus‑small or TextRank extractive to start).
- **Export digest**: weekly markdown/email digest of top storylines, surges, predictions.
- **Quote extraction**: identify quotes + speakers; build a "quote board" UI.
- **Wikidata linking**: disambiguate entities; enrich with descriptions/logos.

---

## 14) Acceptance Criteria

**P1 Complete (MVP)**
- Upload CSV → ingest succeeds; dedups handled.
- `/api/umap` returns ≥ N points with cluster_id for ≥ 80% of articles.
- Galaxy view renders in < 2s on 2k points; hover + click work.
- Timeline brush filters galaxy points live.
- For a selected article, `/api/similar/:id` returns ≥ 5 items with cosine + shared entities/terms.

**P2 Goals (Narrative Intelligence)**
- NER extracts entities from ≥80% of articles; entity timeline view works.
- Storyline threading groups articles into ≥3 tiers; storylines view renders.
- Causal chains detected for known policy events (e.g., EO → Court → Ruling → Impact).
- Entity roles classified with ≥60% confidence on sample set.
- Dashboard shows active/dormant storylines, recent alerts, key actors.

**P3 Goals (Monitoring)**
- Surge detection triggers alerts within 24h of actual surges.
- Dormant story reactivation alerts appear within 6h of first new article.
- Cross-domain bridge articles identified and visualized.
- Dashboard loads state-of-the-world summary in <3s.

**P4 Goals (Prediction)**
- Narrative continuation suggestions have ≥30% accuracy on test set.
- Event impact estimation correlates with actual article volume (R² ≥ 0.4).

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
      similar.py
      timeline.py
      umap.py
      storylines.py       # NEW: story arc endpoints
      causal_chains.py    # NEW: causal chain endpoints
      entities.py         # NEW: entity tracking endpoints
      monitoring.py       # NEW: alerts & anomaly detection
      dashboard.py        # NEW: state-of-the-world summary
    services/
      ingest.py
      embeddings.py
      clustering.py
      ner.py              # NEW: NER implementation + entity roles
      labeling.py
      umap_projection.py
      storylines.py       # NEW: multi-tier storyline threading
      causal_chains.py    # NEW: event chain detection
      monitoring.py       # NEW: anomaly/surge detection
      dashboard.py        # NEW: aggregate stats
    db.py                 # SQLite setup and schema
    config.py             # Configuration
    tests/
  static/
    index.html
    css/
      styles.css
    js/
      main.js
      api.js
      views/
        galaxy.js
        timeline.js
        list.js
        storylines.js     # NEW: river plot
        chains.js         # NEW: causal graph
        dashboard.js      # NEW: monitoring view
        entityTimeline.js # NEW: entity track view
  data/
    faiss.index
    faiss_mapping.npy
    summarized_output.csv
  tools/
    ingest_csv.py
    run_pipeline.py
  requirements.txt
  pytest.ini
```

---

## 17) Implementation Notes & Defaults

- **Similarity threshold**: start at 0.60; expose via `.env`.
- **Storyline tiers**: Tier 1 ≥0.85, Tier 2 0.65-0.84, Tier 3 0.50-0.64.
- **Temporal windows**: Tier 1 ±3 days, Tier 2 ±7 days.
- **Clustering**: HDBSCAN `min_cluster_size=8`, `min_samples=1`; seed UMAP for stability.
- **UMAP**: `n_neighbors=15`, `min_dist=0.1`, `metric='cosine'`.
- **KeyBERT**: top 10 per cluster; keep top 3 as labels.
- **Entity filtering**: drop stop‑entities (`United States`, `Monday`, `America`, etc.).
- **FTS5**: `tokenize = porter unicode61`.
- **Causal chain threshold**: similarity 0.45-0.70 with shared entities + temporal order.
- **Surge detection**: week-over-week growth >50% triggers alert.
- **Dormant threshold**: storyline with no articles >14 days = dormant.

---

## 18) Open Questions (to validate while building)

- Is offline use a hard requirement (i.e., model downloads pre‑baked)?
- Any specific outlets/entities to whitelist or blacklist?
- Preferred chart palettes / accessibility constraints (high contrast)?
- Export formats needed (CSV/PNG/PDF)?
- What constitutes a "surge" for your use case? (% growth threshold)
- How far back should predictive models look? (window size for pattern matching)

---

## 19) Quick Setup Script (outline)

1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python -m spacy download en_core_web_sm`
4. `python tools/ingest_csv.py data/summarized_output.csv`
5. `python tools/build_indexes.py` (embeddings → FAISS; UMAP; clusters)
6. `vite dev` (serve frontend) + `flask --app backend/app run`

---

## 20) Phase Implementation Guides

See separate design documents for detailed implementation:
- `docs/phase2-storylines.md` - Story Arc Detection implementation
- `docs/phase2-causal-chains.md` - Causal Chain Discovery implementation
- `docs/phase2-entities.md` - Entity Tracking & NER implementation
- `docs/phase3-monitoring.md` - Anomaly Detection & Monitoring implementation
- `docs/phase3-dashboard.md` - State-of-the-World Dashboard implementation

---

This spec is intentionally practical and incremental so we can ship value quickly (Galaxy + Timeline), then deepen into narrative intelligence (Storylines, Causal Chains, Monitoring) without re‑architecting.

