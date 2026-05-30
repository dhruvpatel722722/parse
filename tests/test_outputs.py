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
    """Test that exactly 200 records were recovered."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    assert len(data) == 200, f"Expected 200 records, got {len(data)}"


def test_record_structure():
    """Test that all records have the required fields."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for i, rec in enumerate(data):
        assert "id" in rec, f"Record {i} missing 'id'"
        assert "source" in rec, f"Record {i} missing 'source'"
        assert "payload" in rec, f"Record {i} missing 'payload'"
        assert isinstance(rec["id"], int), f"Record {i} id should be int"
        assert isinstance(rec["source"], str), f"Record {i} source should be str"
        assert isinstance(rec["payload"], str), f"Record {i} payload should be str"


def test_records_sorted_by_id():
    """Test that records are sorted by id in ascending order."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    ids = [r["id"] for r in data]
    assert ids == list(range(200)), "Record ids should be 0-199 in order"


def test_source_format():
    """Test that source strings follow the expected pattern."""
    pattern = re.compile(r'^[a-z]+\.[a-z]+\.[0-9a-f]{8}$')
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert pattern.match(rec["source"]), f"Source format invalid: {rec['source']}"


def test_payload_format():
    """Test that payload strings contain expected structured fields."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert "ts=" in rec["payload"], f"Payload missing ts=: {rec['payload'][:30]}"
        assert "len=" in rec["payload"], f"Payload missing len=: {rec['payload'][:40]}"
        assert "sig=" in rec["payload"], f"Payload missing sig=: {rec['payload'][:50]}"


def test_content_matches_reference():
    """Test that recovered data exactly matches the reference."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    assert len(recovered) == len(reference), "Record count mismatch"
    for i, (rec, ref) in enumerate(zip(recovered, reference)):
        assert rec["id"] == ref["id"], f"Record {i} id mismatch"
        assert rec["source"] == ref["source"], f"Record {i} source mismatch"
        assert rec["payload"] == ref["payload"], f"Record {i} payload mismatch"


def test_output_hash_matches():
    """Test that the SHA-256 hash of output matches reference hash."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)
    rec_hash = hashlib.sha256(json.dumps(recovered, sort_keys=True).encode()).hexdigest()
    ref_hash = hashlib.sha256(json.dumps(reference, sort_keys=True).encode()).hexdigest()
    assert rec_hash == ref_hash, "Output hash does not match reference"
