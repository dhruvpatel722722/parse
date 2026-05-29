import json
import os
from pathlib import Path
from datetime import datetime


def test_report_file_exists():
    """Test that the output report JSON file was created."""
    assert os.path.exists("/app/output/report.json"), "Report file /app/output/report.json does not exist"


def test_report_is_valid_json():
    """Test that the report file contains valid parseable JSON."""
    with open("/app/output/report.json", "r") as f:
        content = f.read()
    data = json.loads(content)
    assert isinstance(data, dict), "Report should be a JSON object"


def test_report_has_required_keys():
    """Test that the report contains all required top-level keys."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    required = {"total_events", "by_level", "by_service", "time_range", "multi_line_events", "daily_counts"}
    missing = required - set(data.keys())
    assert not missing, f"Report missing keys: {missing}"


def test_total_events_count():
    """Test that total_events reflects the correct number of log entries including multi-line."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    assert data["total_events"] == 20, f"Expected 20 total events, got {data['total_events']}"


def test_by_level_counts():
    """Test that events are correctly grouped by severity level."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    by_level = data["by_level"]
    assert by_level.get("ERROR") == 7, f"Expected 7 ERROR events, got {by_level.get('ERROR')}"
    assert by_level.get("WARN") == 4, f"Expected 4 WARN events, got {by_level.get('WARN')}"
    assert by_level.get("INFO") == 9, f"Expected 9 INFO events, got {by_level.get('INFO')}"


def test_by_service_structure():
    """Test that all services are present with count and error_rate fields."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    services = data["by_service"]
    expected_services = {"auth-service", "api-gateway", "payment-svc"}
    assert set(services.keys()) == expected_services, f"Expected services {expected_services}, got {set(services.keys())}"
    for svc, stats in services.items():
        assert "count" in stats, f"Service {svc} missing 'count'"
        assert "error_rate" in stats, f"Service {svc} missing 'error_rate'"


def test_by_service_counts():
    """Test that per-service event counts are correct."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    services = data["by_service"]
    assert services["auth-service"]["count"] == 9, f"auth-service count wrong: {services['auth-service']['count']}"
    assert services["api-gateway"]["count"] == 6, f"api-gateway count wrong: {services['api-gateway']['count']}"
    assert services["payment-svc"]["count"] == 5, f"payment-svc count wrong: {services['payment-svc']['count']}"


def test_error_rate_calculation():
    """Test that error_rate is calculated as fraction of errors within each service."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    services = data["by_service"]
    # auth-service: 3 errors out of 9 events = 0.3333
    auth_rate = services["auth-service"]["error_rate"]
    assert abs(auth_rate - 3/9) < 0.01, f"auth-service error_rate wrong: {auth_rate}, expected {3/9:.4f}"
    # api-gateway: 2 errors out of 6 events = 0.3333
    gw_rate = services["api-gateway"]["error_rate"]
    assert abs(gw_rate - 2/6) < 0.01, f"api-gateway error_rate wrong: {gw_rate}, expected {2/6:.4f}"
    # payment-svc: 2 errors out of 5 events = 0.4
    pay_rate = services["payment-svc"]["error_rate"]
    assert abs(pay_rate - 2/5) < 0.01, f"payment-svc error_rate wrong: {pay_rate}, expected {2/5:.4f}"


def test_time_range_format():
    """Test that time_range start and end are valid UTC ISO-8601 timestamps."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    tr = data["time_range"]
    start = datetime.fromisoformat(tr["start"])
    end = datetime.fromisoformat(tr["end"])
    assert start < end, "start should be before end"
    # Verify UTC (offset should be +00:00)
    assert "+00:00" in tr["start"] or "Z" in tr["start"], f"start not in UTC: {tr['start']}"
    assert "+00:00" in tr["end"] or "Z" in tr["end"], f"end not in UTC: {tr['end']}"


def test_time_range_values():
    """Test that the time range covers the expected period from the log files."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    tr = data["time_range"]
    start = datetime.fromisoformat(tr["start"])
    end = datetime.fromisoformat(tr["end"])
    # First log: 2024-03-15T10:30:45+05:30 = 2024-03-15T05:00:45+00:00
    assert start.year == 2024 and start.month == 3 and start.day == 15, f"Unexpected start date: {start}"
    assert start.hour == 5 and start.minute == 0, f"Unexpected start time: {start}"
    # Last log: 2024-03-16T08:04:30-04:00 = 2024-03-16T12:04:30+00:00
    assert end.year == 2024 and end.month == 3 and end.day == 16, f"Unexpected end date: {end}"
    assert end.hour == 12 and end.minute == 4, f"Unexpected end time: {end}"


def test_multi_line_events_count():
    """Test that multi-line events (stack traces) are correctly identified and counted."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    assert data["multi_line_events"] == 4, f"Expected 4 multi-line events, got {data['multi_line_events']}"


def test_daily_counts_keys():
    """Test that daily_counts has entries for each day with events in YYYY-MM-DD format."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    daily = data["daily_counts"]
    # Events span March 15 (UTC) and March 16 (UTC)
    assert "2024-03-15" in daily, f"Missing 2024-03-15 in daily_counts: {daily}"
    assert "2024-03-16" in daily, f"Missing 2024-03-16 in daily_counts: {daily}"
    assert len(daily) == 2, f"Expected 2 days, got {len(daily)}: {daily}"


def test_daily_counts_values():
    """Test that the number of events per day is correct based on UTC timestamps."""
    with open("/app/output/report.json", "r") as f:
        data = json.load(f)
    daily = data["daily_counts"]
    assert daily["2024-03-15"] == 10, f"Expected 10 events on 2024-03-15, got {daily['2024-03-15']}"
    assert daily["2024-03-16"] == 10, f"Expected 10 events on 2024-03-16, got {daily['2024-03-16']}"


def test_report_not_corrupted():
    """Test that the JSON file contains exactly one JSON object (not appended duplicates)."""
    with open("/app/output/report.json", "r") as f:
        content = f.read().strip()
    # Should parse as single object
    data = json.loads(content)
    assert isinstance(data, dict), "Report should be a single JSON object"
    # Check no trailing data
    assert content.count('"total_events"') == 1, "Report appears to have duplicate data (append bug)"
