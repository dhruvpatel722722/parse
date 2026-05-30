import json
import os
import hashlib
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
    """Test that exactly 250 records were recovered."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    assert len(data) == 250, f"Expected 250 records, got {len(data)}"


def test_record_structure():
    """Test that all records have the required fields with correct types."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for i, rec in enumerate(data):
        assert "id" in rec, f"Record {i} missing 'id'"
        assert "field1" in rec, f"Record {i} missing 'field1'"
        assert "field2" in rec, f"Record {i} missing 'field2'"
        assert isinstance(rec["id"], int), f"Record {i} id should be int"
        assert isinstance(rec["field1"], str), f"Record {i} field1 should be str"
        assert isinstance(rec["field2"], str), f"Record {i} field2 should be str"


def test_records_sorted_by_id():
    """Test that records are sorted by id in ascending order."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    ids = [r["id"] for r in data]
    assert ids == list(range(250)), "Record ids should be 0-249 in order"


def test_field1_format():
    """Test that field1 strings follow the expected structured pattern."""
    pattern = re.compile(r'^[\w-]+\.[\w-]+\.[0-9a-f]{8}$')
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert pattern.match(rec["field1"]), f"field1 format invalid: {rec['field1']}"


def test_field2_format():
    """Test that field2 strings contain expected structured telemetry fields."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert "val=" in rec["field2"], f"field2 missing val=: {rec['field2'][:20]}"
        assert "ts=" in rec["field2"], f"field2 missing ts=: {rec['field2'][:30]}"
        assert "chk=" in rec["field2"], f"field2 missing chk=: {rec['field2'][:40]}"


def test_content_matches_reference():
    """Test that recovered data exactly matches the reference."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    assert len(recovered) == len(reference), "Record count mismatch"
    for i, (rec, ref) in enumerate(zip(recovered, reference)):
        assert rec["id"] == ref["id"], f"Record {i} id mismatch"
        assert rec["field1"] == ref["field1"], f"Record {i} field1 mismatch"
        assert rec["field2"] == ref["field2"], f"Record {i} field2 mismatch"


def test_output_hash_matches():
    """Test that the SHA-256 hash of output matches reference hash."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    rec_hash = hashlib.sha256(json.dumps(recovered, sort_keys=True).encode()).hexdigest()
    ref_hash = hashlib.sha256(json.dumps(reference, sort_keys=True).encode()).hexdigest()
    assert rec_hash == ref_hash, "Output hash does not match reference"
