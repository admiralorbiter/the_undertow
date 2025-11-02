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
**Status:** Not started  
**Priority:** HIGH  
**See:** `docs/phase2-entities.md`

Implement:
- Extract PERSON, ORG, GPE entities using spaCy
- Track entity mentions chronologically per article
- Classify entity roles (protagonist, antagonist, subject, adjudicator)
- Build entity timeline view
- Filter articles by entity

**Estimated effort:** 2-3 days

### P2.2: Story Arc Detection
**Status:** Not started  
**Priority:** HIGH  
**See:** `docs/phase2-storylines.md`

Implement:
- Multi-tier storyline threading (Tier 1-3 relationships)
- Union-Find grouping algorithm
- Momentum scoring (active vs. dormant vs. concluded)
- Storylines river/Sankey visualization
- Storyline API endpoints

**Estimated effort:** 3-4 days

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
**Status:** Not started  
**Priority:** HIGH  
**See:** `docs/phase3-dashboard.md`

Implement:
- Active storylines panel
- Recent alerts feed
- Temporal heatmap
- Key actors list
- Cluster evolution chart
- Quick stats summary

**Estimated effort:** 2-3 days

### P3.2: Anomaly Detection
**Status:** Not started  
**Priority:** MEDIUM  
**See:** `docs/phase3-monitoring.md`

Implement:
- Topic surge detection (>50% growth)
- Dormant story reactivation alerts
- New actor emergence
- Narrative divergence detection
- Alert system

**Estimated effort:** 3-4 days

## Future: P4 - Prediction

**Status:** Stretch goals  
**Priority:** LOW

- Narrative continuation prediction
- Event impact estimation
- Temporal forecasting
- Sentiment tracking

---

## Implementation Guide

1. Start with **NER** (entities.md) - foundation for other features
2. Build **Storylines** (storylines.md) - core narrative tracking
3. Create **Dashboard** (dashboard.md) - monitoring interface you'll use daily
4. Add **Monitoring** (monitoring.md) - alerts and anomaly detection
5. Optionally tackle **Causal Chains** - complex but powerful

## Data Insights from Your Corpus

Your data (3,574 articles, Feb-Oct 2025) shows:
- Heavy focus on political events, policy changes, institutional conflicts
- Recurring actors: Trump, Musk, agencies, judges
- Rich policy chains: EO → Court → Ruling → Impact patterns
- Temporal surge patterns waiting to be detected

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
