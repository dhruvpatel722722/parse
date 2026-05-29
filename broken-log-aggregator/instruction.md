There's a slow query engine at `/app/engine/` that processes search queries against an in-memory dataset. It works correctly but is too slow.

Run it with: `python /app/engine/bench.py`

It will execute a benchmark of queries and report timing. Your task is to optimize the engine so the full benchmark completes in under 2.0 seconds while still producing correct results.

The engine has these files:
- `bench.py` — benchmark runner (do not modify)
- `index.py` — builds the search index from raw data
- `query.py` — executes queries against the index
- `data.py` — loads the dataset

The dataset at `/app/data/records.json` contains 200,000 records with fields: `id`, `title`, `tags`, `score`, `timestamp`. The benchmark runs queries that:
1. Filter by tag combinations (AND/OR logic)
2. Filter by score ranges
3. Filter by timestamp ranges
4. Sort results by different fields
5. Apply pagination (offset + limit)

Current performance is around 15-25 seconds for the full benchmark. You need to get it under 2.0 seconds.

Constraints:
- You must NOT modify `bench.py` or `/app/data/records.json`
- The query results must remain identical (same records, same order)
- All optimizations must be in `index.py` and/or `query.py`
- Write your optimized files to `/app/engine/index.py` and `/app/engine/query.py`

After optimizing, run the benchmark again to verify it passes. The benchmark writes results to `/app/output/bench_result.json`.
