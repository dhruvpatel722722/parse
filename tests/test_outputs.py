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
    """Test that exactly 150 records were recovered."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    assert len(data) == 150, f"Expected 150 records, got {len(data)}"


def test_record_structure():
    """Test that all records have the required id, category, and message fields."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for i, rec in enumerate(data):
        assert "id" in rec, f"Record {i} missing 'id'"
        assert "category" in rec, f"Record {i} missing 'category'"
        assert "message" in rec, f"Record {i} missing 'message'"
        assert isinstance(rec["id"], int), f"Record {i} id should be int"
        assert isinstance(rec["category"], str), f"Record {i} category should be str"
        assert isinstance(rec["message"], str), f"Record {i} message should be str"


def test_records_sorted_by_id():
    """Test that records are sorted by id in ascending order."""
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    ids = [r["id"] for r in data]
    assert ids == sorted(ids), "Records are not sorted by id"
    assert ids == list(range(150)), "Record ids should be 0-149"


def test_categories_are_valid():
    """Test that recovered categories are from the expected set."""
    valid_cats = {"auth", "network", "storage", "compute", "deploy",
                  "monitor", "backup", "sync", "alert", "config"}
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert rec["category"] in valid_cats, f"Invalid category: {rec['category']}"


def test_messages_have_expected_format():
    """Test that recovered messages contain the expected timestamp and id fields."""
    import re
    pattern = re.compile(r'^.+ .+ ts=\d{8} id=[0-9a-f]{12}$')
    with open("/app/output/recovered.json") as f:
        data = json.load(f)
    for rec in data:
        assert pattern.match(rec["message"]), f"Message format invalid: {rec['message'][:40]}"


def test_content_matches_reference():
    """Test that recovered data exactly matches the reference generated during build."""
    with open("/app/output/recovered.json") as f:
        recovered = json.load(f)
    with open("/var/lib/tbench/.reference.json") as f:
        reference = json.load(f)

    assert len(recovered) == len(reference), "Record count mismatch"

    for i, (rec, ref) in enumerate(zip(recovered, reference)):
        assert rec["id"] == ref["id"], f"Record {i} id mismatch"
        assert rec["category"] == ref["category"], f"Record {i} category mismatch"
        assert rec["message"] == ref["message"], f"Record {i} message mismatch"


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
