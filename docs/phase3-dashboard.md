# Phase 3: State-of-the-World Dashboard

## Overview

Single-pane view of "what's happening now" - active storylines, alerts, temporal heatmap, key actors, cluster evolution. Quick snapshot of system state.

## Goals

- Display top active/dormant storylines
- Show recent alerts
- Temporal heatmap (article density by day)
- Top entities by activity
- Cluster evolution chart
- Quick stats summary

## Technical Design

### Dashboard Data

Aggregate data from multiple sources:
- Storylines (active, dormant counts)
- Alerts (recent, unacknowledged)
- Articles (temporal distribution)
- Entities (mention counts)
- Clusters (size over time)

### API Endpoint

**GET /api/dashboard/summary**

Returns:
```json
{
  "active_storylines": [{...}],  // Top 10
  "recent_alerts": [{...}],       // Last 24h
  "temporal_heatmap": [{date, count}],
  "key_actors": [{entity_id, name, mentions_7d}],  // Top 20
  "cluster_evolution": [{date, cluster_sizes}],
  "stats": {
    "total_articles": int,
    "active_storylines_count": int,
    "dormant_storylines_count": int,
    "recent_alerts_count": int,
    "new_articles_7d": int
  }
}
```

## Service Implementation

**File:** `backend/services/dashboard.py`

Single method: `get_dashboard_summary()` - queries all sources and aggregates.

## Frontend View

**File:** `static/js/views/dashboard.js`

Layout:
- Top: Stats cards (total articles, active storylines, etc.)
- Left: Active storylines list
- Right: Recent alerts
- Center: Temporal heatmap
- Bottom: Key actors + cluster evolution chart

Uses ECharts for visualizations.

## Implementation Priority

**HIGH** - This is the monitoring interface you'll use daily. Start here after P2 basics are done.
