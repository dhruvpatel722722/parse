import json
import hashlib
import os
import re


def test_recover_script_exists():
    """Test that the recovery script was created."""
    assert os.path.exists("/app/recover.py"), "recover.py does not exist"


def test_output_file_exists():
    """Test that the recovered JSON output was produced."""
    assert os.path.exists("/app/output/recovered.json"), "recovered.json does not exist"


def test_output_is_valid_json():
    """Test that the output file contains valid parseable JSON."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    assert isinstance(data, list), "Output should be a JSON array"


def test_record_count():
    """Test that exactly 200 records were recovered."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    assert len(data) == 200, f"Expected 200 records, got {len(data)}"


def test_record_structure():
    """Test that all records have the required id, key, and value fields."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for i, record in enumerate(data):
        assert "id" in record, f"Record {i} missing 'id' field"
        assert "key" in record, f"Record {i} missing 'key' field"
        assert "value" in record, f"Record {i} missing 'value' field"
        assert isinstance(record["id"], int), f"Record {i} 'id' should be int"
        assert isinstance(record["key"], str), f"Record {i} 'key' should be str"
        assert isinstance(record["value"], str), f"Record {i} 'value' should be str"


def test_records_sorted_by_id():
    """Test that records are sorted by id in ascending order."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    ids = [r["id"] for r in data]
    assert ids == sorted(ids), "Records not sorted by id"
    assert ids == list(range(200)), "IDs should be 0-199"



def test_keys_have_expected_format():
    """Test that recovered keys follow the word.word.NNN pattern."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^[a-z]+\.[a-z]+\.\d{3}$')
    for i, record in enumerate(data):
        assert pattern.match(record["key"]), (
            f"Record {i} key '{record['key']}' doesn't match word.word.NNN pattern"
        )


def test_values_have_expected_format():
    """Test that recovered values contain the expected data structure."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^data=[0-9a-f]{16}, seq=\d+, hash=[0-9a-f]{8}$')
    for i, record in enumerate(data):
        assert pattern.match(record["value"]), (
            f"Record {i} value '{record['value']}' doesn't match expected format"
        )


def test_content_matches_reference():
    """Test that recovered data exactly matches the reference generated during build."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    assert len(recovered) == len(reference), "Record count mismatch"
    for i, (rec, ref) in enumerate(zip(recovered, reference)):
        assert rec["id"] == ref["id"], f"Record {i}: id mismatch"
        assert rec["key"] == ref["key"], f"Record {i}: key mismatch '{rec['key']}' vs '{ref['key']}'"
        assert rec["value"] == ref["value"], f"Record {i}: value mismatch"


def test_output_hash_matches():
    """Test that the SHA-256 hash of the output matches the expected reference hash."""
    with open("/app/output/recovered.json") as f:
        recovered_content = f.read()
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    # Normalize: re-serialize reference the same way
    expected_content = json.dumps(reference, indent=2)
    recovered_hash = hashlib.sha256(recovered_content.encode()).hexdigest()
    expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()
    assert recovered_hash == expected_hash, (
        f"Hash mismatch: got {recovered_hash[:16]}... expected {expected_hash[:16]}..."
    )
