# Implementation Documentation

This directory contains detailed design documents for each development phase.

## Overview

See `tech+design.md` in project root for the complete system architecture. These docs provide phase-specific implementation details.

## Phase 2: Narrative Intelligence

### 2.1 Entity Tracking & NER
**File:** `phase2-entities.md`

Implement Named Entity Recognition with spaCy, track entity mentions over time, and classify entity roles (protagonist, antagonist, subject, adjudicator).

**Key Components:**
- NER extraction service
- Entity role classification
- Entity timeline API
- Stoplist filtering

### 2.2 Story Arc Detection
**File:** `phase2-storylines.md`

Detect multi-tier storylines: near-duplicates, continuations, and related developments. Track narrative momentum and status.

**Key Components:**
- Union-Find storyline grouping
- Three-tier relationship detection
- Momentum scoring
- Storylines API and visualization

### 2.3 Causal Chain Discovery
**File:** `phase2-causal-chains.md`

Identify Event A → B → C sequences using temporal ordering, similarity, and entity overlap.

**Priority:** LOW - complex, can defer to after basics are working

## Phase 3: Monitoring & Alerting

### 3.1 Anomaly Detection
**File:** `phase3-monitoring.md`

Detect topic surges, dormant story reactivation, new actor emergence, and narrative divergence.

**Key Components:**
- Surge detection algorithm
- Alert generation
- Background monitoring job
- Alert API

### 3.2 State-of-the-World Dashboard
**File:** `phase3-dashboard.md`

Aggregate view of system state: active storylines, alerts, key actors, cluster evolution.

**Key Components:**
- Dashboard data aggregation
- Multi-widget layout
- Real-time stats

## Implementation Order

**Recommended sequence:**

1. **NER Implementation** (entities.md)
   - Extract entities from articles
   - Basic entity tracking
   - Foundation for other features

2. **Storyline Detection** (storylines.md)
   - Multi-tier grouping
   - Momentum scoring
   - Storylines view

3. **Dashboard** (dashboard.md)
   - Basic monitoring interface
   - Shows what's happening now

4. **Monitoring** (monitoring.md)
   - Surge detection
   - Alert system

5. **Causal Chains** (causal-chains.md) - Optional/defer

## Getting Started

Each design doc includes:
- Overview and goals
- Database schema changes
- Service implementation skeleton
- API endpoint specs
- Frontend view outlines
- Testing strategies

Start with the entities doc, then storylines, then dashboard.

## Questions?

See `tech+design.md` §18 for open questions to validate during implementation.
