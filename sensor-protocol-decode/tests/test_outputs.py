import json
import os
import hashlib


def test_decode_script_exists():
    """Test that the decode script was created at the expected path."""
    assert os.path.exists("/app/decode.py"), "decode.py does not exist"


def test_output_file_exists():
    """Test that the decoded readings JSON output was produced."""
    assert os.path.exists("/app/output/readings.json"), "readings.json does not exist"


def test_output_is_valid_json():
    """Test that the output file contains valid parseable JSON."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Output should be a JSON object"


def test_output_has_required_keys():
    """Test that the output contains sensors, total_packets, and checksum_failures."""
    with open("/app/output/readings.json") as f:
        data = json.load(f)
    required = {"sensors", "total_packets", "checksum_failures"}
    missing = required - set(data.keys())
    assert not missing, f"Output missing keys: {missing}"


def test_total_packets_matches():
    """Test that the total packet count matches the reference."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert output["total_packets"] == ref["total_packets"], (
        f"total_packets: got {output['total_packets']}, expected {ref['total_packets']}"
    )


def test_checksum_failures_matches():
    """Test that the checksum failure count matches the reference."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert output["checksum_failures"] == ref["checksum_failures"], (
        f"checksum_failures: got {output['checksum_failures']}, expected {ref['checksum_failures']}"
    )


def test_sensor_count():
    """Test that the correct number of sensors were decoded."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert len(output["sensors"]) == len(ref["sensors"]), (
        f"Sensor count: got {len(output['sensors'])}, expected {len(ref['sensors'])}"
    )


def test_sensor_readings_match():
    """Test that all sensor readings exactly match the reference values."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    
    for sid, ref_data in ref["sensors"].items():
        assert sid in output["sensors"], f"Missing sensor {sid}"
        out_data = output["sensors"][sid]
        assert out_data["readings"] == ref_data["readings"], (
            f"Sensor {sid} readings mismatch: got {len(out_data['readings'])} values, "
            f"expected {len(ref_data['readings'])}"
        )


def test_sensor_stats_match():
    """Test that avg, min, max statistics for each sensor are correct."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    
    for sid, ref_data in ref["sensors"].items():
        out_data = output["sensors"][sid]
        assert abs(out_data["avg"] - ref_data["avg"]) < 0.01, (
            f"Sensor {sid} avg: got {out_data['avg']}, expected {ref_data['avg']}"
        )
        assert abs(out_data["min"] - ref_data["min"]) < 0.01, (
            f"Sensor {sid} min: got {out_data['min']}, expected {ref_data['min']}"
        )
        assert abs(out_data["max"] - ref_data["max"]) < 0.01, (
            f"Sensor {sid} max: got {out_data['max']}, expected {ref_data['max']}"
        )


def test_output_hash_matches_reference():
    """Test that the full output content matches the reference via hash comparison."""
    with open("/app/output/readings.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    
    out_canonical = json.dumps(output, sort_keys=True)
    ref_canonical = json.dumps(ref, sort_keys=True)
    
    out_hash = hashlib.sha256(out_canonical.encode()).hexdigest()
    ref_hash = hashlib.sha256(ref_canonical.encode()).hexdigest()
    
    assert out_hash == ref_hash, "Output does not match reference (hash mismatch)"
