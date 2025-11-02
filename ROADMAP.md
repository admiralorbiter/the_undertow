# Project Roadmap: Narrative Intelligence System

## Vision

Transform the News Relationship Explorer into a **Narrative Intelligence System** for tracking how news stories evolve, connect, and impact real-world events over time.

## Completed: P0 & P1 ✓

- CSV ingestion and deduplication
- SQLite database with FTS5 search
- Embeddings (MiniLM-L6-v2) + FAISS index
- Similarity graph construction
- HDBSCAN clustering + KeyBERT labeling
- UMAP 2D projection
- Galaxy view (scatter plot)
- Timeline view (temporal distribution)
- Basic article search and filtering

## Next: P2 - Narrative Intelligence

Focus on tracking **how stories develop** and **who's involved**.

### P2.1: Entity Tracking & NER
**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**See:** `docs/phase2-entities.md`

✅ Implemented:
- Extract PERSON, ORG, GPE entities using spaCy (1,374 entities from 581 articles)
- Track entity mentions chronologically per article
- Entity role classification foundation (protagonist, antagonist, subject, adjudicator)
- Entity timeline API
- Filter/search entities by type, name, degree

**Result:** Backend complete, APIs working, ready for frontend integration

### P2.2: Story Arc Detection
**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**See:** `docs/phase2-storylines.md`

✅ Implemented:
- Multi-tier storyline threading (Tier 1-3 relationships)
- Union-Find grouping algorithm
- Momentum scoring (active vs. dormant vs. concluded)
- Storyline API endpoints
- 61 storylines detected from 152 articles

**Result:** Backend complete, 61 storylines created, APIs working

### P2.3: Causal Chain Discovery
**Status:** Not started  
**Priority:** LOW (defer)  
**See:** `docs/phase2-causal-chains.md`

Implement:
- Detect Event A → B → C sequences
- Classify chain types (Policy, Actor, Institutional)
- Score chain strength
- Causal graph visualization

**Estimated effort:** 5-7 days  
**Note:** Complex feature, can start simple and refine later

## Then: P3 - Monitoring & Alerting

Focus on **detecting unusual patterns** and **surfacing insights**.

### P3.1: State-of-the-World Dashboard
**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**See:** `docs/phase3-dashboard.md`

✅ Implemented:
- Active storylines panel (top 5 by momentum)
- Temporal heatmap (ECharts calendar visualization)
- Key actors list (top 20 entities, last 7 days)
- Cluster evolution chart (stacked area visualization)
- Quick stats summary (5 metrics)
- Date range selector (7d/30d/90d/All)
- Full-width dashboard layout

**Result:** Dashboard complete with ECharts visualizations, responsive design, and real-time data

### P3.2: Anomaly Detection
**Status:** ✅ COMPLETE  
**Priority:** MEDIUM  
**See:** `docs/phase3-monitoring.md`

✅ Implemented:
- Topic surge detection (>50% growth, week-over-week comparison)
- Dormant story reactivation alerts (>14 days quiet → new articles)
- New actor emergence (zero historical mentions → recent activity)
- Alert management system (acknowledge, filter by type/severity)
- Alerts API endpoints and dedicated frontend view
- Dashboard integration (unacknowledged alerts count)

**Result:** Complete anomaly detection with 3 detection types, alert management, and timeline UI

## Future: P4 - Prediction

**Status:** Stretch goals  
**Priority:** LOW

- Narrative continuation prediction
- Event impact estimation
- Temporal forecasting
- Sentiment tracking

---

## Implementation Guide

1. ✅ **NER** (entities.md) - foundation for other features - COMPLETE
2. ✅ **Storylines** (storylines.md) - core narrative tracking - COMPLETE
3. ✅ **Dashboard** (dashboard.md) - monitoring interface - COMPLETE
4. ✅ **Monitoring** (monitoring.md) - alerts and anomaly detection - COMPLETE
5. **Next:** Optionally tackle **Causal Chains** - complex but powerful

## Data Insights from Your Corpus

Your data (581 articles processed, Feb-Oct 2025) shows:
- Heavy focus on political events, policy changes, institutional conflicts
- Recurring actors: Trump (312 mentions), U.S. (159 mentions), multiple other key entities
- **61 storylines detected** covering narrative evolution across topics
- Rich similarity patterns with 1,162 edges identified
- 13 major topic clusters discovered

Perfect dataset for narrative intelligence!

## Key Files

- `tech+design.md` - Complete system architecture (updated)
- `docs/README.md` - Implementation docs index
- `docs/phase2-*.md` - Phase 2 implementation guides
- `docs/phase3-*.md` - Phase 3 implementation guides
- `ROADMAP.md` - This file

## Questions?

See `tech+design.md` §18 for open questions to validate during implementation.

---

Last updated: Based on vision pivot Nov 2025
