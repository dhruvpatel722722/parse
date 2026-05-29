#!/usr/bin/env python3
"""Generate the slow query engine and dataset."""
import os
import json
import random
import hashlib

os.makedirs("/app/engine", exist_ok=True)
os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# === Generate dataset: 50000 records ===
random.seed(42)
TAGS = ["python", "java", "rust", "go", "javascript", "typescript", "c++", "ruby",
        "sql", "docker", "kubernetes", "aws", "linux", "git", "api", "web",
        "mobile", "security", "testing", "devops"]
SERVICES = ["auth", "payment", "search", "analytics", "notifications", "storage"]

records = []
for i in range(200000):
    num_tags = random.randint(1, 5)
    tags = random.sample(TAGS, num_tags)
    score = round(random.uniform(0, 100), 2)
    # Timestamps spread over 365 days in 2024
    day = random.randint(0, 364)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    ts = f"2024-{(day // 30) + 1:02d}-{(day % 30) + 1:02d}T{hour:02d}:{minute:02d}:00Z"
    title = f"Record {i} - {random.choice(SERVICES)} {random.choice(['issue', 'feature', 'task', 'bug', 'improvement'])}"
    records.append({
        "id": i,
        "title": title,
        "tags": tags,
        "score": score,
        "timestamp": ts,
    })

with open("/app/data/records.json", "w") as f:
    json.dump(records, f)

# === data.py — simple data loader ===
with open("/app/engine/data.py", "w") as f:
    f.write('''import json

def load_records(path="/app/data/records.json"):
    """Load records from JSON file."""
    with open(path) as f:
        return json.load(f)
''')

# === index.py — intentionally naive, no indexing ===
with open("/app/engine/index.py", "w") as f:
    f.write('''from data import load_records

class SearchIndex:
    """A search index over the records dataset."""
    
    def __init__(self):
        self.records = load_records()
    
    def get_all_records(self):
        """Return all records (no indexing, just raw data)."""
        return self.records
    
    def get_records_by_tag(self, tag):
        """Linear scan to find records with a given tag."""
        return [r for r in self.records if tag in r["tags"]]
    
    def get_records_in_score_range(self, min_score, max_score):
        """Linear scan for score range."""
        return [r for r in self.records if min_score <= r["score"] <= max_score]
    
    def get_records_in_time_range(self, start, end):
        """Linear scan for timestamp range."""
        return [r for r in self.records if start <= r["timestamp"] <= end]
''')

# === query.py — intentionally slow query execution ===
with open("/app/engine/query.py", "w") as f:
    f.write("""from index import SearchIndex

class QueryEngine:
    \"\"\"Execute queries against the search index.\"\"\"
    
    def __init__(self):
        self.index = SearchIndex()
    
    def execute(self, query):
        \"\"\"Execute a query dict and return matching records.\"\"\"
        results = self.index.get_all_records().copy()
        
        # Filter by tags (AND logic: must have ALL specified tags)
        if "tags_all" in query:
            for tag in query["tags_all"]:
                results = [r for r in results if tag in r["tags"]]
        
        # Filter by tags (OR logic: must have ANY specified tag)
        if "tags_any" in query:
            required_tags = set(query["tags_any"])
            results = [r for r in results if required_tags.intersection(r["tags"])]
        
        # Filter by score range
        if "min_score" in query:
            results = [r for r in results if r["score"] >= query["min_score"]]
        if "max_score" in query:
            results = [r for r in results if r["score"] <= query["max_score"]]
        
        # Filter by timestamp range
        if "start_time" in query:
            results = [r for r in results if r["timestamp"] >= query["start_time"]]
        if "end_time" in query:
            results = [r for r in results if r["timestamp"] <= query["end_time"]]
        
        # Sort
        if "sort_by" in query:
            field = query["sort_by"]
            reverse = query.get("sort_desc", False)
            results.sort(key=lambda r: r[field], reverse=reverse)
        
        # Pagination
        offset = query.get("offset", 0)
        limit = query.get("limit", len(results))
        results = results[offset:offset + limit]
        
        return results
""")

# === bench.py — benchmark runner (agent must NOT modify this) ===
with open("/app/engine/bench.py", "w") as f:
    f.write('''import json
import time
import sys
import os
import hashlib

sys.path.insert(0, "/app/engine")
from query import QueryEngine

QUERIES = [
    # Tag AND queries
    {"tags_all": ["python", "docker"], "sort_by": "score", "sort_desc": True, "limit": 100},
    {"tags_all": ["rust", "linux"], "sort_by": "timestamp", "limit": 50},
    {"tags_all": ["javascript", "web", "api"], "sort_by": "score", "limit": 20},
    # Tag OR queries
    {"tags_any": ["kubernetes", "docker", "devops"], "min_score": 50, "sort_by": "score", "sort_desc": True, "limit": 200},
    {"tags_any": ["python", "rust", "go"], "max_score": 30, "sort_by": "timestamp", "limit": 150},
    # Score range queries
    {"min_score": 80, "max_score": 100, "sort_by": "score", "sort_desc": True, "limit": 500},
    {"min_score": 0, "max_score": 10, "sort_by": "timestamp", "sort_desc": True, "limit": 100},
    # Timestamp range queries
    {"start_time": "2024-06-01T00:00:00Z", "end_time": "2024-06-30T23:59:00Z", "sort_by": "score", "sort_desc": True, "limit": 100},
    {"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-03-31T23:59:00Z", "tags_any": ["python", "java"], "sort_by": "timestamp", "limit": 200},
    # Combined complex queries
    {"tags_all": ["python"], "min_score": 60, "start_time": "2024-03-01T00:00:00Z", "end_time": "2024-09-30T23:59:00Z", "sort_by": "score", "sort_desc": True, "limit": 50},
    {"tags_any": ["security", "testing"], "min_score": 40, "max_score": 80, "sort_by": "timestamp", "sort_desc": True, "limit": 100, "offset": 50},
    {"tags_all": ["go", "api"], "max_score": 70, "sort_by": "title", "limit": 30},
    # Pagination-heavy queries
    {"tags_any": ["python", "java", "javascript", "typescript"], "sort_by": "score", "sort_desc": True, "limit": 100, "offset": 500},
    {"min_score": 20, "max_score": 80, "sort_by": "timestamp", "limit": 50, "offset": 1000},
    {"tags_any": ["docker", "kubernetes", "aws"], "sort_by": "score", "limit": 200, "offset": 200},
    # Repeat queries to test consistency
    {"tags_all": ["python", "docker"], "sort_by": "score", "sort_desc": True, "limit": 100},
    {"tags_any": ["kubernetes", "docker", "devops"], "min_score": 50, "sort_by": "score", "sort_desc": True, "limit": 200},
    {"min_score": 80, "max_score": 100, "sort_by": "score", "sort_desc": True, "limit": 500},
    # High-selectivity queries
    {"tags_all": ["python", "security", "testing"], "sort_by": "score", "sort_desc": True, "limit": 10},
    {"tags_all": ["rust", "kubernetes"], "min_score": 70, "sort_by": "timestamp", "limit": 20},
]

def compute_result_hash(results):
    """Compute a deterministic hash of query results for validation."""
    canonical = json.dumps(results, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]

def run_benchmark():
    engine = QueryEngine()
    
    total_start = time.time()
    all_results = []
    query_times = []
    
    for iteration in range(3):
        for i, query in enumerate(QUERIES):
            start = time.time()
            result = engine.execute(query)
            elapsed = time.time() - start
            query_times.append(elapsed)
            if iteration == 0:
                all_results.append({
                    "query_index": i,
                    "num_results": len(result),
                    "hash": compute_result_hash(result),
                    "time_ms": round(elapsed * 1000, 2),
                })
    
    total_time = time.time() - total_start
    
    bench_result = {
        "total_time_seconds": round(total_time, 3),
        "passed": total_time < 2.0,
        "num_queries": len(QUERIES),
        "query_results": all_results,
    }
    
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/bench_result.json", "w") as f:
        json.dump(bench_result, f, indent=2)
    
    print(f"Benchmark complete: {total_time:.3f}s ({'PASSED' if total_time < 2.0 else 'FAILED'})")
    print(f"Target: < 2.0s")
    for i, qt in enumerate(query_times[:len(QUERIES)]):
        print(f"  Query {i:2d}: {qt*1000:8.2f}ms ({all_results[i]['num_results']} results)")
    
    return bench_result

if __name__ == "__main__":
    run_benchmark()
''')

print("Generated query engine at /app/engine/")
print("Generated dataset at /app/data/records.json")

# Store hash of bench.py for tamper detection
import hashlib
with open("/app/engine/bench.py", "rb") as f:
    bench_hash = hashlib.sha256(f.read()).hexdigest()[:16]
with open("/app/data/.bench_hash", "w") as f:
    f.write(bench_hash)
