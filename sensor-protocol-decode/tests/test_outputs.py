import json
import os
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
    required_keys = {"seq", "sensor", "timestamp", "value"}
    for i, record in enumerate(data):
        missing = required_keys - set(record.keys())
        assert not missing, f"Record {i} missing keys: {missing}"


def test_sequential_ids():
    """Test that seq values are 0-299 in order."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    seqs = [r["seq"] for r in data]
    assert seqs == list(range(300)), "Sequence numbers should be 0-299 in order"


def test_sensor_names_valid():
    """Test that sensor names match expected format."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^(temp|pressure|humidity|flow|vibration)-[A-F][1-9]$')
    for i, record in enumerate(data):
        assert pattern.match(record["sensor"]), (
            f"Record {i} sensor '{record['sensor']}' doesn't match expected pattern"
        )


def test_timestamps_valid():
    """Test that timestamps are valid ISO-8601 UTC format."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^2024-03-\d{2}T\d{2}:\d{2}:\d{2}Z$')
    for i, record in enumerate(data):
        assert pattern.match(record["timestamp"]), (
            f"Record {i} timestamp '{record['timestamp']}' doesn't match expected format"
        )



def test_values_in_range():
    """Test that all values are in the physically plausible range."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    for i, record in enumerate(data):
        val = record["value"]
        assert isinstance(val, (int, float)), f"Record {i} value is not numeric"
        assert 0 <= val <= 1000, (
            f"Record {i} value {val} outside plausible range [0, 1000]"
        )


def test_content_matches_reference():
    """Test that the output exactly matches the reference data."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)

    assert len(output) == len(reference), (
        f"Output has {len(output)} records, reference has {len(reference)}"
    )

    for i, (out_rec, ref_rec) in enumerate(zip(output, reference)):
        assert out_rec["seq"] == ref_rec["seq"], (
            f"Record {i}: seq mismatch {out_rec['seq']} != {ref_rec['seq']}"
        )
        assert out_rec["sensor"] == ref_rec["sensor"], (
            f"Record {i}: sensor mismatch '{out_rec['sensor']}' != '{ref_rec['sensor']}'"
        )
        assert out_rec["timestamp"] == ref_rec["timestamp"], (
            f"Record {i}: timestamp mismatch '{out_rec['timestamp']}' != '{ref_rec['timestamp']}'"
        )
        assert abs(out_rec["value"] - ref_rec["value"]) < 1e-4, (
            f"Record {i}: value mismatch {out_rec['value']} != {ref_rec['value']}"
        )
