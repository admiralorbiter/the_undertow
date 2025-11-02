# Testing Guide for P1 MVP

## Quick Verification

### 1. Start the Application
```bash
python app.py
```

The server will start on `http://127.0.0.1:5000`

### 2. Test API Endpoints (Manual)

Open these URLs in your browser or use curl/Postman:

**Clusters API:**
```
http://127.0.0.1:5000/api/clusters
```
- Should return 13 clusters with labels
- Check that each cluster has: id, label, size, score

**UMAP API:**
```
http://127.0.0.1:5000/api/umap
```
- Should return 581 points with x, y coordinates
- Each point should have: id, x, y, cluster_id
- Verify meta information shows model name and UMAP params

**Timeline API:**
```
http://127.0.0.1:5000/api/timeline
```
- Should return bins array with date counts
- Check by_cluster breakdown per bin

**Similar Articles:**
```
http://127.0.0.1:5000/api/similar/1
```
- Replace `1` with any article ID
- Should return similar articles with:
  - cosine similarity score
  - shared_terms
  - date_proximity_days
  - same_outlet flag

### 3. Test Frontend Views

Open `http://localhost:5000` in your browser:

#### List View (Default)
- ✅ Articles should load and display
- ✅ Search bar should work
- ✅ Date filters should work
- ✅ Pagination should work
- ✅ Click article → details panel shows on right

#### Galaxy View
1. Click "Galaxy" tab
2. **Expected:**
   - Scatter plot with 581 points rendered
   - Points colored by cluster (13 different colors + gray for unclustered)
   - Hover over point → tooltip shows article ID and position
   - Click a point → article details appear in right panel
   - Zoom and pan should work (use mouse wheel, drag)
   - Legend should show all clusters

3. **Things to check:**
   - Points are not all clustered together (good spread)
   - Different clusters are visually distinct
   - Performance: should load smoothly, no lag

#### Timeline View
1. Click "Timeline" tab
2. **Expected:**
   - Line/area chart showing article counts over time
   - Multiple series (one per cluster + unclustered + total)
   - X-axis shows dates (2025-02, 2025-03, etc.)
   - Y-axis shows article counts
   - Tooltip on hover shows exact counts

3. **Things to check:**
   - Chart loads within 2-3 seconds
   - All clusters visible in legend
   - Can zoom using data zoom slider
   - Can brush/select time range

#### Explain-Why Panel
1. Click any article in List or Galaxy view
2. **Expected in Details Panel:**
   - Article title, summary, outlet, date
   - "Similar Articles" section appears
   - Each similar article shows:
     - Title (clickable link)
     - Similarity percentage (e.g., "87.5%")
     - Shared terms/keywords
     - Date proximity (e.g., "5 days")
     - "Same outlet" badge if applicable

3. **Things to check:**
   - Similar articles are actually related (check titles)
   - Shared terms make sense
   - Similarity scores are reasonable (0-100%)
   - Date proximity is accurate

### 4. Automated Tests

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/unit/ -v          # Unit tests
pytest tests/integration/ -v   # Integration tests

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

**Expected:**
- All tests should pass
- Coverage should be reasonable for implemented features

### 5. Data Quality Checks

```python
# Quick data verification script
python -c "
from backend.db import get_db
conn = get_db()
cursor = conn.cursor()

# Check embeddings
cursor.execute('SELECT COUNT(*) FROM embeddings')
print(f'Embeddings: {cursor.fetchone()[0]}')

# Check clusters
cursor.execute('SELECT id, label, size FROM clusters ORDER BY size DESC LIMIT 5')
print('\nTop 5 clusters:')
for row in cursor.fetchall():
    print(f'  Cluster {row[\"id\"]}: {row[\"label\"]} ({row[\"size\"]} articles)')

# Check UMAP coverage
cursor.execute('SELECT COUNT(*) FROM articles WHERE umap_x IS NOT NULL')
print(f'\nArticles with UMAP: {cursor.fetchone()[0]}')

# Check similarity graph
cursor.execute('SELECT COUNT(*) FROM similarities')
print(f'Similarity edges: {cursor.fetchone()[0]}')

conn.close()
"
```

### 6. Common Issues & Fixes

**Issue: Galaxy view shows "No UMAP Data"**
- Fix: Run `python tools/run_pipeline.py --step 6 --force`

**Issue: Clusters have "Unlabeled" labels**
- Fix: Run `python tools/run_pipeline.py --step 7 --force`

**Issue: Timeline is empty**
- Fix: Check that articles have valid `date_bin` values
- Run ingestion again to ensure date_bin is populated

**Issue: Similar articles not showing**
- Fix: Run `python tools/run_pipeline.py --step 4 --force` to rebuild similarity graph

**Issue: Charts not rendering**
- Check browser console for errors
- Verify ECharts library loaded (check Network tab)
- Try hard refresh (Ctrl+F5)

### 7. Performance Checks

**Galaxy View:**
- Should load 581 points in < 2 seconds
- Should be interactive (zoom/pan) without lag
- Memory usage should be reasonable

**Timeline View:**
- Should render chart in < 1 second
- Should handle brushing smoothly

**API Response Times:**
```bash
# Test API response times
time curl http://127.0.0.1:5000/api/clusters
time curl http://127.0.0.1:5000/api/umap
time curl http://127.0.0.1:5000/api/timeline
```

All should respond in < 500ms.

### 8. Visual Verification Checklist

- [ ] Galaxy view: Points are spread out, not all in one spot
- [ ] Galaxy view: Different clusters have different colors
- [ ] Galaxy view: Hover shows tooltip with article info
- [ ] Galaxy view: Click selects article and shows details
- [ ] Timeline: Shows article distribution over time
- [ ] Timeline: Multiple clusters visible as different series
- [ ] Timeline: Can zoom and brush time range
- [ ] Details panel: Shows similar articles with explain-why info
- [ ] Details panel: Shared terms make sense for the articles
- [ ] Details panel: Date proximity is accurate
- [ ] List view: Search and filters still work
- [ ] List view: Articles show cluster_id if they have one

## Success Criteria

✅ All 8 chunks implemented
✅ Pipeline runs successfully (581 articles processed)
✅ 13 clusters created with meaningful labels
✅ 1162 similarity edges created
✅ All 581 articles have UMAP coordinates
✅ Frontend views render correctly
✅ Explain-why panel shows relationship evidence
✅ No JavaScript errors in browser console
✅ API endpoints return correct data
✅ Tests pass

## Next Steps

Once verified:
1. Test with different datasets
2. Adjust clustering parameters if needed (min_cluster_size, etc.)
3. Tune similarity threshold if too many/few edges
4. Consider adding cluster filtering to Galaxy view
5. Add export functionality if needed
6. Prepare for P2 features (NER, Entity graphs, Storylines)

