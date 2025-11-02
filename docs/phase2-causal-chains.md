# Phase 2: Causal Chain Discovery

## Overview

Identify event sequences (Event A → Event B → Event C) using temporal ordering, semantic similarity, entity overlap, and causal language patterns. Track policy chains, actor chains, and institutional chains.

## Goals

- Detect causal relationships between articles
- Classify chain types (Policy, Actor, Institutional)
- Score chain strength/confidence
- Visualize causal flows over time
- Enable upstream/downstream exploration

## Technical Design

### Database Schema

**Table: `causal_chains`**
```sql
CREATE TABLE causal_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    articles_json TEXT NOT NULL,  -- JSON array of article_ids in order
    chain_type TEXT CHECK(chain_type IN ('Policy Chain', 'Actor Chain', 'Institutional Chain', 'Mixed')),
    strength_score REAL DEFAULT 0.0,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    evidence_json TEXT  -- JSON with detection evidence
);

CREATE INDEX idx_causal_chains_dates ON causal_chains(start_date, end_date);
CREATE INDEX idx_causal_chains_type ON causal_chains(chain_type);
```

### Detection Logic

**Criteria for causal link:**
1. Temporal ordering: A.date < B.date
2. Semantic continuity: 0.45 ≤ cosine ≤ 0.70 (not duplicates, but related)
3. Shared entities: at least 2 overlapping entities
4. Causal language (optional but strengthens confidence)

**Chain Types:**
- **Policy Chain**: EO → Court Challenge → Ruling → Impact
- **Actor Chain**: Person X does Y → Reaction Z → Counter-action W
- **Institutional Chain**: Agency A → Congress B → Court C

**Strength Scoring:**
```
strength = (temporal_weight * sim_weight * entity_weight) + causal_bonus

Where:
- temporal_weight = 1 / (days_apart + 1)
- sim_weight = cosine_score
- entity_weight = shared_entities / 5 (capped)
- causal_bonus = 0.2 if causal language detected
```

## Service Implementation

**File:** `backend/services/causal_chains.py` (skeleton)

Key methods:
- `detect_chains()` - Main detection logic
- `classify_chain_type()` - Determine chain category
- `calculate_strength()` - Score chain confidence
- `check_causal_language()` - Regex pattern matching

## API Endpoints

- `GET /api/chains` - List all chains
- `GET /api/article/:id/upstream` - Predecessors
- `GET /api/article/:id/downstream` - Successors
- `GET /api/chain/:id` - Chain details

## Frontend View

**File:** `static/js/views/chains.js`

Visualize as node-link graph with temporal flow (left-to-right or top-to-bottom).

## Implementation Priority

**LOW** - Complex to implement well. Can start with simple temporal + similarity detection and refine later.
