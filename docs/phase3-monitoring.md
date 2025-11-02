# Phase 3: Anomaly Detection & Monitoring

## Overview

Detect unusual patterns in article flow: topic surges, dormant story reactivation, new actor emergence, narrative divergence. Generate alerts for noteworthy events.

## Goals

- Topic surge detection (>50% week-over-week growth)
- Dormant story reactivation alerts (>14 days quiet → new articles)
- New actor emergence (frequent in recent window, absent historically)
- Narrative divergence (contradictory patterns in similar stories)
- Alert management and severity classification

## Technical Design

### Database Schema

**Table: `alerts`**
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT CHECK(alert_type IN ('topic_surge', 'story_reactivation', 'new_actor', 'divergence')) NOT NULL,
    entity_json TEXT NOT NULL,  -- JSON with context
    triggered_at TEXT NOT NULL,  -- ISO timestamp
    description TEXT NOT NULL,
    severity TEXT CHECK(severity IN ('low', 'medium', 'high')) DEFAULT 'medium',
    acknowledged BOOLEAN DEFAULT 0
);

CREATE INDEX idx_alerts_triggered ON alerts(triggered_at DESC);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_severity ON alerts(severity);
```

## Detection Algorithms

### Topic Surge Detection

```python
def detect_surges():
    # For each cluster:
    #   - Get article counts in last 7 days
    #   - Get article counts in previous 7 days
    #   - If (current / previous) > 1.5: SURGE
    pass
```

### Dormant Story Reactivation

```python
def detect_reactivations():
    # For storylines marked 'dormant':
    #   - Check if any articles in last 7 days
    #   - If yes: ALERT
    pass
```

### New Actor Emergence

```python
def detect_new_actors():
    # For entities mentioned in last 7 days:
    #   - Count mentions in recent window
    #   - Check if absent before that
    #   - If mentions > 5 and historically absent: ALERT
    pass
```

## Service Implementation

**File:** `backend/services/monitoring.py`

Key methods:
- `run_detections()` - Execute all detection algorithms
- `check_surges()` - Topic surge detection
- `check_reactivations()` - Storyline reactivation
- `check_new_actors()` - Actor emergence
- `create_alert()` - Store alert in database

## API Endpoints

- `GET /api/alerts` - List recent alerts
- `GET /api/monitoring/stats` - Aggregated statistics
- `POST /api/alerts/:id/acknowledge` - Mark alert as read

## Background Job

Run monitoring checks:
- After new article ingestion
- On-demand via endpoint
- Scheduled (daily cron)

## Implementation Priority

**MEDIUM** - Start simple: check surges and reactivations. Add divergence detection later.
