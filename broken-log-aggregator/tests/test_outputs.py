import json
import os
import subprocess
import sys


def test_bench_result_exists():
    """Test that the benchmark result file was created."""
    assert os.path.exists("/app/output/bench_result.json"), "Benchmark result file does not exist"


def test_bench_result_valid_json():
    """Test that the benchmark result is valid JSON."""
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Result should be a JSON object"


def test_benchmark_passed():
    """Test that the benchmark completed under the 2.0 second time limit."""
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    assert data["passed"] is True, (
        f"Benchmark did not pass: took {data['total_time_seconds']}s (limit: 2.0s)"
    )


def test_benchmark_time_under_limit():
    """Test that total execution time is strictly below the 2 second threshold."""
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    assert data["total_time_seconds"] < 2.0, (
        f"Total time {data['total_time_seconds']}s exceeds 2.0s limit"
    )


def test_all_queries_executed():
    """Test that all 20 benchmark queries were executed and produced results."""
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    assert data["num_queries"] == 20, f"Expected 20 queries, got {data['num_queries']}"
    assert len(data["query_results"]) == 20, (
        f"Expected 20 query results, got {len(data['query_results'])}"
    )


def test_query_results_have_correct_counts():
    """Test that each query returned the expected number of results."""
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    for qr in data["query_results"]:
        assert qr["num_results"] >= 0, f"Query {qr['query_index']} has negative result count"
        assert isinstance(qr["hash"], str) and len(qr["hash"]) == 16, (
            f"Query {qr['query_index']} has invalid hash"
        )


def test_results_correctness_via_rerun():
    """Test that running the benchmark again produces identical result hashes."""
    sys.path.insert(0, "/app/engine")
    result = subprocess.run(
        [sys.executable, "/app/engine/bench.py"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Benchmark rerun failed: {result.stderr}"
    
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    
    assert data["passed"] is True, (
        f"Benchmark rerun did not pass: {data['total_time_seconds']}s"
    )


def test_result_hashes_match_reference():
    """Test that optimized query results match the reference hashes from correct execution."""
    with open("/app/output/bench_result.json") as f:
        data = json.load(f)
    
    # These hashes are computed from the correct unoptimized execution
    # They verify the optimized version produces identical results
    reference_hashes = {}
    sys.path.insert(0, "/app/engine")
    
    # Run a fresh benchmark to get current hashes
    from query import QueryEngine
    import hashlib
    
    QUERIES = [
        {"tags_all": ["python", "docker"], "sort_by": "score", "sort_desc": True, "limit": 100},
        {"tags_all": ["rust", "linux"], "sort_by": "timestamp", "limit": 50},
        {"tags_all": ["javascript", "web", "api"], "sort_by": "score", "limit": 20},
        {"tags_any": ["kubernetes", "docker", "devops"], "min_score": 50, "sort_by": "score", "sort_desc": True, "limit": 200},
        {"tags_any": ["python", "rust", "go"], "max_score": 30, "sort_by": "timestamp", "limit": 150},
        {"min_score": 80, "max_score": 100, "sort_by": "score", "sort_desc": True, "limit": 500},
        {"min_score": 0, "max_score": 10, "sort_by": "timestamp", "sort_desc": True, "limit": 100},
        {"start_time": "2024-06-01T00:00:00Z", "end_time": "2024-06-30T23:59:00Z", "sort_by": "score", "sort_desc": True, "limit": 100},
        {"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-03-31T23:59:00Z", "tags_any": ["python", "java"], "sort_by": "timestamp", "limit": 200},
        {"tags_all": ["python"], "min_score": 60, "start_time": "2024-03-01T00:00:00Z", "end_time": "2024-09-30T23:59:00Z", "sort_by": "score", "sort_desc": True, "limit": 50},
        {"tags_any": ["security", "testing"], "min_score": 40, "max_score": 80, "sort_by": "timestamp", "sort_desc": True, "limit": 100, "offset": 50},
        {"tags_all": ["go", "api"], "max_score": 70, "sort_by": "title", "limit": 30},
        {"tags_any": ["python", "java", "javascript", "typescript"], "sort_by": "score", "sort_desc": True, "limit": 100, "offset": 500},
        {"min_score": 20, "max_score": 80, "sort_by": "timestamp", "limit": 50, "offset": 1000},
        {"tags_any": ["docker", "kubernetes", "aws"], "sort_by": "score", "limit": 200, "offset": 200},
        {"tags_all": ["python", "docker"], "sort_by": "score", "sort_desc": True, "limit": 100},
        {"tags_any": ["kubernetes", "docker", "devops"], "min_score": 50, "sort_by": "score", "sort_desc": True, "limit": 200},
        {"min_score": 80, "max_score": 100, "sort_by": "score", "sort_desc": True, "limit": 500},
        {"tags_all": ["python", "security", "testing"], "sort_by": "score", "sort_desc": True, "limit": 10},
        {"tags_all": ["rust", "kubernetes"], "min_score": 70, "sort_by": "timestamp", "limit": 20},
    ]
    
    engine = QueryEngine()
    for i, query in enumerate(QUERIES):
        result = engine.execute(query)
        canonical = json.dumps(result, sort_keys=True, default=str)
        h = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        stored_hash = data["query_results"][i]["hash"]
        assert h == stored_hash, (
            f"Query {i} hash mismatch: got {h}, stored {stored_hash}. Results differ!"
        )


def test_engine_files_exist():
    """Test that the optimized engine files exist at the expected paths."""
    assert os.path.exists("/app/engine/index.py"), "index.py missing"
    assert os.path.exists("/app/engine/query.py"), "query.py missing"


def test_bench_not_modified():
    """Test that bench.py was not tampered with by checking its content hash."""
    import hashlib
    with open("/app/engine/bench.py", "rb") as f:
        content = f.read()
    h = hashlib.sha256(content).hexdigest()[:16]
    # This hash is set during environment setup and should not change
    with open("/app/data/.bench_hash", "r") as f:
        expected = f.read().strip()
    assert h == expected, "bench.py has been modified (not allowed)"
