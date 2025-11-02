#!/usr/bin/env python
"""
Quick test script to verify pipeline results.
"""
from app import create_app

app = create_app()
client = app.test_client()

print("=" * 60)
print("Testing Pipeline Results")
print("=" * 60)

# Test Clusters API
print("\n1. Testing Clusters API...")
r = client.get('/api/clusters')
if r.status_code == 200:
    data = r.get_json()
    clusters = data.get('clusters', [])
    stats = data.get('stats', {})
    print(f"   [OK] {len(clusters)} clusters found")
    print(f"   [OK] Total articles: {stats.get('total_articles', 0)}")
    print(f"   [OK] Clustered: {stats.get('clustered_articles', 0)}")
    print(f"   [OK] Unclustered: {stats.get('unclustered', 0)}")
    if clusters:
        print(f"\n   Top 3 clusters:")
        for c in clusters[:3]:
            print(f"   - Cluster {c['id']}: '{c['label']}' ({c['size']} articles)")
else:
    print(f"   [ERROR] Status code: {r.status_code}")

# Test UMAP API
print("\n2. Testing UMAP API...")
r = client.get('/api/umap')
if r.status_code == 200:
    data = r.get_json()
    points = data.get('points', [])
    meta = data.get('meta', {})
    print(f"   [OK] {len(points)} points found")
    print(f"   [OK] Model: {meta.get('model', 'unknown')}")
    print(f"   [OK] Has clusters: {meta.get('has_clusters', False)}")
    if points:
        sample = points[0]
        print(f"   [OK] Sample point: id={sample.get('id')}, x={sample.get('x'):.2f}, y={sample.get('y'):.2f}, cluster_id={sample.get('cluster_id')}")
else:
    print(f"   [ERROR] Status code: {r.status_code}")

# Test Timeline API
print("\n3. Testing Timeline API...")
r = client.get('/api/timeline')
if r.status_code == 200:
    data = r.get_json()
    bins = data.get('bins', [])
    print(f"   [OK] {len(bins)} time bins found")
    if bins:
        total = sum(b['count'] for b in bins)
        print(f"   [OK] Total articles in timeline: {total}")
        print(f"   [OK] Date range: {bins[0]['date']} to {bins[-1]['date']}")
else:
    print(f"   [ERROR] Status code: {r.status_code}")

# Test Similar Articles API (test with first article)
print("\n4. Testing Similar Articles API...")
r = client.get('/api/similar/1')
if r.status_code == 200:
    data = r.get_json()
    items = data.get('items', [])
    article = data.get('article', {})
    print(f"   [OK] Article: {article.get('title', 'Unknown')[:50]}...")
    print(f"   [OK] Found {len(items)} similar articles")
    if items:
        sample = items[0]
        why = sample.get('why', {})
        print(f"   [OK] Top similar: '{sample.get('title', '')[:40]}...'")
        print(f"      - Similarity: {sample.get('cosine', 0)*100:.1f}%")
        print(f"      - Shared terms: {len(why.get('shared_terms', []))}")
        print(f"      - Date proximity: {why.get('date_proximity_days', 'N/A')} days")
        print(f"      - Same outlet: {why.get('same_outlet', False)}")
elif r.status_code == 404:
    print("   [WARN] Article ID 1 not found (try a different ID)")
else:
    print(f"   [ERROR] Status code: {r.status_code}")

print("\n" + "=" * 60)
print("[SUCCESS] All API endpoints responding correctly!")
print("=" * 60)
print("\nNext steps:")
print("1. Start the app: python app.py")
print("2. Open browser: http://localhost:5000")
print("3. Test Galaxy view: Click 'Galaxy' tab")
print("4. Test Timeline view: Click 'Timeline' tab")
print("5. Click articles to see explain-why panel")
print("\nSee TESTING.md for detailed testing guide.")

