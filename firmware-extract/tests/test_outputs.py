import json
import os
import hashlib


def test_extract_script_exists():
    """Test that the extraction script was created."""
    assert os.path.exists("/app/extract.py"), "extract.py does not exist"


def test_output_file_exists():
    """Test that the config JSON output was produced."""
    assert os.path.exists("/app/output/config.json"), "config.json does not exist"


def test_output_is_valid_json():
    """Test that the output is valid parseable JSON."""
    with open("/app/output/config.json") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Output should be a JSON object"


def test_has_required_keys():
    """Test that the config has device_id, sensors, network, and version fields."""
    with open("/app/output/config.json") as f:
        data = json.load(f)
    required = {"device_id", "sensors", "network", "version"}
    missing = required - set(data.keys())
    assert not missing, f"Config missing keys: {missing}"


def test_device_id():
    """Test that the extracted device_id matches the reference."""
    with open("/app/output/config.json") as f:
        data = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert data["device_id"] == ref["device_id"], (
        f"device_id mismatch: got '{data['device_id']}'"
    )


def test_sensors_count_and_structure():
    """Test that all sensors are present with correct fields."""
    with open("/app/output/config.json") as f:
        data = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert len(data["sensors"]) == len(ref["sensors"]), (
        f"Sensor count: got {len(data['sensors'])}, expected {len(ref['sensors'])}"
    )
    for i, (s, r) in enumerate(zip(data["sensors"], ref["sensors"])):
        assert s["name"] == r["name"], f"Sensor {i} name mismatch"
        assert s["pin"] == r["pin"], f"Sensor {i} pin mismatch"
        assert abs(s["calibration"] - r["calibration"]) < 0.001, f"Sensor {i} calibration mismatch"


def test_network_config():
    """Test that network configuration matches the reference."""
    with open("/app/output/config.json") as f:
        data = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert data["network"] == ref["network"], (
        f"Network mismatch: got {data['network']}"
    )


def test_version():
    """Test that the firmware version string matches."""
    with open("/app/output/config.json") as f:
        data = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    assert data["version"] == ref["version"], (
        f"Version mismatch: got '{data['version']}', expected '{ref['version']}'"
    )


def test_output_matches_reference_hash():
    """Test that the full output matches the reference via canonical hash."""
    with open("/app/output/config.json") as f:
        output = json.load(f)
    with open("/app/data/.reference.json") as f:
        ref = json.load(f)
    
    out_str = json.dumps(output, sort_keys=True)
    ref_str = json.dumps(ref, sort_keys=True)
    
    assert hashlib.sha256(out_str.encode()).hexdigest() == hashlib.sha256(ref_str.encode()).hexdigest(), (
        "Output does not match reference"
    )
