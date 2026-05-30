import json
import os
import hashlib


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
    for i, rec in enumerate(data):
        assert "id" in rec, f"Record {i} missing 'id'"
        assert "key" in rec, f"Record {i} missing 'key'"
        assert "value" in rec, f"Record {i} missing 'value'"
        assert isinstance(rec["id"], int), f"Record {i} id should be int"
        assert isinstance(rec["key"], str), f"Record {i} key should be str"
        assert isinstance(rec["value"], str), f"Record {i} value should be str"


def test_records_sorted_by_id():
    """Test that records are sorted by id in ascending order."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    ids = [r["id"] for r in data]
    assert ids == sorted(ids), "Records are not sorted by id"
    assert ids == list(range(200)), "Record ids should be 0-199"


def test_keys_have_expected_format():
    """Test that recovered keys follow the word.word.NNN pattern."""
    import re
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    pattern = re.compile(r'^[a-z]+\.[a-z]+\.\d{3}$')
    for rec in data:
        assert pattern.match(rec["key"]), f"Key '{rec['key']}' doesn't match expected pattern"


def test_values_have_expected_format():
    """Test that recovered values contain the expected data structure."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert "data=" in rec["value"], f"Value missing 'data=' prefix: {rec['value'][:30]}"
        assert "seq=" in rec["value"], f"Value missing 'seq=': {rec['value'][:50]}"
        assert "hash=" in rec["value"], f"Value missing 'hash=': {rec['value'][:50]}"


def test_content_matches_reference():
    """Test that recovered data exactly matches the reference generated during build."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    
    assert len(recovered) == len(reference), "Record count mismatch"
    
    for i, (rec, ref) in enumerate(zip(recovered, reference)):
        assert rec["id"] == ref["id"], f"Record {i} id mismatch"
        assert rec["key"] == ref["key"], f"Record {i} key mismatch: got '{rec['key']}' expected '{ref['key']}'"
        assert rec["value"] == ref["value"], f"Record {i} value mismatch at record {i}"


def test_output_hash_matches():
    """Test that the SHA-256 hash of the output matches the expected reference hash."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    
    rec_canonical = json.dumps(recovered, sort_keys=True)
    ref_canonical = json.dumps(reference, sort_keys=True)
    
    rec_hash = hashlib.sha256(rec_canonical.encode()).hexdigest()
    ref_hash = hashlib.sha256(ref_canonical.encode()).hexdigest()
    
    assert rec_hash == ref_hash, "Output hash does not match reference"
