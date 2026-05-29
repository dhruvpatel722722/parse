import json
import os
import hashlib
import re


def test_extract_script_exists():
    """Test that the extraction script was created."""
    assert os.path.exists("/app/extract.py"), "extract.py does not exist"


def test_output_file_exists():
    """Test that the readings JSON output was produced."""
    assert os.path.exists("/app/output/readings.json"), "readings.json does not exist"


def test_output_is_valid_json():
    """Test that the output is a valid JSON array."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    assert isinstance(data, list), "Output should be a JSON array"


def test_record_count():
    """Test that exactly 300 records were extracted."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    assert len(data) == 300, f"Expected 300 records, got {len(data)}"


def test_record_structure():
    """Test that all records have seq, sensor, timestamp, and value fields."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    for i, rec in enumerate(data):
        assert "seq" in rec, f"Record {i} missing 'seq'"
        assert "sensor" in rec, f"Record {i} missing 'sensor'"
        assert "timestamp" in rec, f"Record {i} missing 'timestamp'"
        assert "value" in rec, f"Record {i} missing 'value'"


def test_sequential_ids():
    """Test that seq values are 0-299 in order."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    seqs = [r["seq"] for r in data]
    assert seqs == list(range(300)), "Seq values should be 0-299 in order"


def test_sensor_names_valid():
    """Test that sensor names match expected format."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^(temp|pressure|humidity|flow|vibration)-[A-F]\d$')
    for rec in data:
        assert pattern.match(rec["sensor"]), f"Invalid sensor name: {rec['sensor']}"


def test_timestamps_valid():
    """Test that timestamps are valid ISO-8601 UTC format."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
    for rec in data:
        assert pattern.match(rec["timestamp"]), f"Invalid timestamp: {rec['timestamp']}"


def test_values_in_range():
    """Test that all values are in the physically plausible range."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    for rec in data:
        assert 0 <= rec["value"] <= 1000, f"Value out of range: {rec['value']}"


def test_content_matches_reference():
    """Test that the output exactly matches the reference data."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        ref = json.load(f)

    out_str = json.dumps(output, sort_keys=True)
    ref_str = json.dumps(ref, sort_keys=True)
    assert hashlib.sha256(out_str.encode()).hexdigest() == hashlib.sha256(ref_str.encode()).hexdigest(), (
        "Output does not match reference"
    )
