#!/usr/bin/env python3
"""Generate the broken log aggregator and sample log files."""
import os

os.makedirs("/app/logagg", exist_ok=True)
os.makedirs("/app/logs", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# === main.py — Bug 1: wrong variable name causes crash on empty config ===
with open("/app/logagg/main.py", "w") as f:
    f.write('''import os
import sys
from parser import parse_log_file
from aggregator import aggregate_records
from writer import write_report

LOG_DIR = "/app/logs"
OUTPUT_PATH = "/app/output/report.json"

def main():
    log_files = sorted([
        os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR)
        if f.endswith(".log")
    ])

    if not log_files:
        print("No log files found")
        sys.exit(1)

    all_records = []
    for fpath in log_files:
        records = parse_log_file(fpath)
        all_records.extend(records)

    # Bug 1: variable name typo - 'result' vs 'results'
    results = aggregate_records(all_records)
    write_report(result, OUTPUT_PATH)
    print(f"Report written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
''')

# === parser.py — Bug 2: regex doesn't handle timezone offsets with colon ===
# === Bug 3: multi-line continuation logic is inverted ===
with open("/app/logagg/parser.py", "w") as f:
    f.write('''import re
from datetime import datetime, timezone, timedelta

# Bug 2: timezone pattern missing colon between hours:minutes
# Pattern expects +0530 but actual logs have +05:30
LOG_PATTERN = re.compile(
    r"^(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{4})\\s+(\\S+)\\s+(ERROR|WARN|INFO)\\s+(.*)$"
)

def parse_timestamp(ts_str):
    """Parse ISO-8601 timestamp with timezone offset to UTC datetime."""
    # Handle +05:30 or -04:00 format
    if ":" == ts_str[-3:-2]:
        ts_str = ts_str[:-3] + ts_str[-2:]
    # Now ts_str is like 2024-03-15T10:30:45+0530
    dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S%z")
    return dt.astimezone(timezone.utc)

def parse_log_file(filepath):
    """Parse a log file into structured records."""
    records = []
    current_record = None

    with open(filepath, "r") as f:
        for line in f:
            line = line.rstrip("\\n")
            match = LOG_PATTERN.match(line)

            if match:
                if current_record:
                    records.append(current_record)
                ts_str, service, level, message = match.groups()
                current_record = {
                    "timestamp": parse_timestamp(ts_str),
                    "service": service,
                    "level": level,
                    "message": message,
                    "is_multiline": False
                }
            # Bug 3: condition inverted — should check if line starts with whitespace
            # but instead checks if it does NOT start with whitespace
            elif current_record and not line.startswith(" "):
                current_record["message"] += "\\n" + line
                current_record["is_multiline"] = True

    if current_record:
        records.append(current_record)

    return records
''')

# === aggregator.py — Bug 4: off-by-one in daily counts (uses local date not UTC) ===
# === Bug 5: error_rate divides by zero when service has no events ===
with open("/app/logagg/aggregator.py", "w") as f:
    f.write('''from collections import defaultdict

def aggregate_records(records):
    """Aggregate parsed log records into summary statistics."""
    by_level = defaultdict(int)
    by_service = defaultdict(lambda: {"count": 0, "errors": 0})
    daily_counts = defaultdict(int)
    multi_line_count = 0

    for rec in records:
        by_level[rec["level"]] += 1

        svc = rec["service"]
        by_service[svc]["count"] += 1
        if rec["level"] == "ERROR":
            by_service[svc]["errors"] += 1

        if rec["is_multiline"]:
            multi_line_count += 1

        # Bug 4: uses .date() which gives local date from the original timezone
        # instead of UTC date — but timestamps are already converted to UTC,
        # however the strftime uses wrong format
        day_key = rec["timestamp"].strftime("%Y-%d-%m")  # Bug: day and month swapped
        daily_counts[day_key] += 1

    # Bug 5: computes error_rate but doesn't handle the case where
    # total_events is used instead of per-service count
    total_events = len(records)
    service_stats = {}
    for svc, data in by_service.items():
        service_stats[svc] = {
            "count": data["count"],
            # Bug: divides errors by total_events instead of service count
            "error_rate": round(data["errors"] / total_events, 4)
        }

    timestamps = [r["timestamp"] for r in records]
    time_range = {
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat(),
    }

    return {
        "total_events": total_events,
        "by_level": dict(by_level),
        "by_service": service_stats,
        "time_range": time_range,
        "multi_line_events": multi_line_count,
        "daily_counts": dict(daily_counts),
    }
''')

# === writer.py — Bug 6: indentation causes invalid JSON (uses tabs not spaces) ===
# Actually let's make it crash on datetime serialization
with open("/app/logagg/writer.py", "w") as f:
    f.write('''import json

def write_report(data, output_path):
    """Write aggregation report to JSON file."""
    # Bug 6: no default serializer for datetime objects in time_range
    # The isoformat() in aggregator should have produced strings,
    # but if timestamps include tzinfo, json.dump will fail on the
    # overall structure check. Instead, let's make a subtler bug:
    # the file is opened in append mode, corrupting output on re-runs
    with open(output_path, "a") as f:  # Bug: "a" instead of "w"
        json.dump(data, f, indent=2)
''')

# === Generate log files with various edge cases ===
log1_content = """2024-03-15T10:30:45+05:30 auth-service ERROR Authentication failed for user admin
2024-03-15T10:30:46+05:30 auth-service ERROR Exception in auth handler
  at auth.validate_token(auth.py:142)
  at middleware.process(middleware.py:38)
2024-03-15T10:31:00+05:30 auth-service INFO User login successful user=john
2024-03-15T10:31:15+05:30 api-gateway WARN Rate limit approaching for client 10.0.0.5
2024-03-15T10:32:00+05:30 api-gateway INFO Request processed in 245ms
2024-03-15T10:32:30+05:30 auth-service WARN Token expiring soon for session abc123
2024-03-15T10:33:00+05:30 payment-svc ERROR Payment processing timeout
  at payment.charge(payment.py:89)
  at handlers.checkout(handlers.py:201)
  caused by: ConnectionTimeout after 30s
2024-03-15T10:33:45+05:30 payment-svc INFO Retry successful for txn-7891
2024-03-15T10:34:00+05:30 api-gateway ERROR Upstream connection refused
2024-03-15T10:34:30+05:30 auth-service INFO Session cleanup completed
"""

log2_content = """2024-03-16T08:00:00-04:00 auth-service INFO Service startup complete
2024-03-16T08:00:15-04:00 api-gateway INFO Health check passed
2024-03-16T08:01:00-04:00 payment-svc WARN Connection pool nearly exhausted
2024-03-16T08:01:30-04:00 auth-service ERROR Database connection lost
  at db.connect(database.py:55)
  at auth.refresh_cache(auth.py:200)
2024-03-16T08:02:00-04:00 api-gateway ERROR Request timeout after 60s
  at proxy.forward(proxy.py:112)
2024-03-16T08:02:30-04:00 payment-svc INFO Connection pool recovered
2024-03-16T08:03:00-04:00 auth-service WARN High memory usage detected: 89%
2024-03-16T08:03:30-04:00 api-gateway INFO Cache invalidation complete
2024-03-16T08:04:00-04:00 payment-svc ERROR Duplicate transaction detected txn-8012
2024-03-16T08:04:30-04:00 auth-service INFO Database reconnected successfully
"""

with open("/app/logs/app-2024-03-15.log", "w") as f:
    f.write(log1_content.strip() + "\n")

with open("/app/logs/app-2024-03-16.log", "w") as f:
    f.write(log2_content.strip() + "\n")

print("Generated broken log aggregator at /app/logagg/")
print("Generated log files at /app/logs/")
