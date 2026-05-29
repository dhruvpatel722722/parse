#!/usr/bin/env python3
"""Generate the broken log aggregator and sample log files."""
import os

os.makedirs("/app/logagg", exist_ok=True)
os.makedirs("/app/logs", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# === main.py — Bug 1: import shadows stdlib 'parser' module ===
# The file imports from local parser.py but on Python 3.13 there's no stdlib parser
# conflict. Real bug: the glob pattern misses files with uppercase .LOG extension
with open("/app/logagg/main.py", "w") as f:
    f.write('''import os
import sys
import glob
from parser import parse_log_file
from aggregator import aggregate_records
from writer import write_report

LOG_DIR = "/app/logs"
OUTPUT_PATH = "/app/output/report.json"

def discover_logs(directory):
    """Find all log files in directory."""
    # Bug 1: only matches .log not .LOG — misses some files
    pattern = os.path.join(directory, "*.log")
    return sorted(glob.glob(pattern))

def main():
    log_files = discover_logs(LOG_DIR)

    if not log_files:
        print("No log files found")
        sys.exit(1)

    all_records = []
    for fpath in log_files:
        records = parse_log_file(fpath)
        all_records.extend(records)

    report = aggregate_records(all_records)
    write_report(report, OUTPUT_PATH)
    print(f"Report written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
''')

# === parser.py ===
# Bug 2: regex uses \\s+ which also matches \\t, but the actual separator
# between timestamp and service could be a tab in some log lines
# Bug 3: multiline detection checks for TAB indent but continuation lines use spaces
# Bug 4: parse_timestamp strips timezone colon ONLY if the third-from-last char is ':'
#         but this breaks for timestamps already in +0000 format (no colon)
#         Actually: the real subtle bug is it converts to UTC but the test expects
#         UTC timestamps — the bug is that when offset is negative, the manual
#         hour adjustment adds instead of subtracting
with open("/app/logagg/parser.py", "w") as f:
    f.write('''import re
from datetime import datetime, timezone, timedelta

LOG_PATTERN = re.compile(
    r"^(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{2}:\\d{2})\\s+(\\S+)\\s+(ERROR|WARN|INFO)\\s+(.*)$"
)

def parse_timestamp(ts_str):
    """Parse ISO-8601 timestamp with timezone to UTC datetime."""
    # Extract offset manually for conversion
    sign = 1 if ts_str[-6] == '+' else -1
    offset_hours = int(ts_str[-5:-3])
    offset_minutes = int(ts_str[-2:])
    base_str = ts_str[:-6]
    
    dt_naive = datetime.strptime(base_str, "%Y-%m-%dT%H:%M:%S")
    # Bug 4: sign is applied wrong — subtracts when should add and vice versa
    # To convert local -> UTC: subtract the offset
    # But code does: utc = local + sign*offset (should be local - sign*offset)
    offset = timedelta(hours=offset_hours, minutes=offset_minutes)
    utc_dt = dt_naive + timedelta(hours=sign * offset_hours, minutes=sign * offset_minutes)
    return utc_dt.replace(tzinfo=timezone.utc)

def parse_log_file(filepath):
    """Parse a log file into structured records."""
    records = []
    current_record = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\\n")
            if not line:
                continue
            
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
            # Bug 3: checks for tab indent but continuation lines use spaces
            elif current_record and line.startswith("\\t"):
                current_record["message"] += "\\n" + line
                current_record["is_multiline"] = True

    if current_record:
        records.append(current_record)

    return records
''')

# === aggregator.py ===
# Bug 5: daily_counts uses the ORIGINAL timestamp date, not the UTC-converted date
#         Since timestamps are already converted to UTC in parser, this is fine...
#         EXCEPT: the counter uses rec["timestamp"].date() but then formats as string
#         using strftime("%Y-%m-%d") — but date() returns a date object and the
#         dict key becomes a date object, not a string!
# Bug 6: error_rate rounds to 2 decimal places but test expects 4
# Bug 7: by_level only counts levels that appear — if no DEBUG events,
#         the key is missing. Test expects all three levels always present
#         Actually let's make bug 7: the level comparison is case-sensitive
#         but some internal processing lowercases it
with open("/app/logagg/aggregator.py", "w") as f:
    f.write('''from collections import defaultdict
from datetime import date

def aggregate_records(records):
    """Aggregate parsed log records into summary statistics."""
    if not records:
        return {
            "total_events": 0,
            "by_level": {"ERROR": 0, "WARN": 0, "INFO": 0},
            "by_service": {},
            "time_range": {"start": "", "end": ""},
            "multi_line_events": 0,
            "daily_counts": {},
        }

    by_level = {"ERROR": 0, "WARN": 0, "INFO": 0}
    by_service = defaultdict(lambda: {"count": 0, "errors": 0})
    daily_counts = defaultdict(int)
    multi_line_count = 0

    for rec in records:
        level = rec["level"]
        by_level[level] = by_level.get(level, 0) + 1

        svc = rec["service"]
        by_service[svc]["count"] += 1
        if rec["level"] == "ERROR":
            by_service[svc]["errors"] += 1

        if rec["is_multiline"]:
            multi_line_count += 1

        # Bug 5: uses .date() which returns a date object as dict key
        # json.dump will fail on date keys — need .strftime("%Y-%m-%d")
        day_key = rec["timestamp"].date()
        daily_counts[day_key] += 1

    total_events = len(records)
    service_stats = {}
    for svc, data in by_service.items():
        service_stats[svc] = {
            "count": data["count"],
            # Bug 6: rounds to 2 decimals, test expects 4 decimal precision
            "error_rate": round(data["errors"] / data["count"], 2)
        }

    timestamps = [r["timestamp"] for r in records]
    time_range = {
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat(),
    }

    return {
        "total_events": total_events,
        "by_level": by_level,
        "by_service": service_stats,
        "time_range": time_range,
        "multi_line_events": multi_line_count,
        "daily_counts": dict(daily_counts),
    }
''')

# === writer.py ===
# Bug 8: json.dump with default=str handles date keys BUT it also stringifies
# everything unexpected — actually let's make the bug that it writes with
# ensure_ascii=True which mangles any unicode in messages, AND
# it doesn't handle date objects so it crashes
with open("/app/logagg/writer.py", "w") as f:
    f.write('''import json
import os

def write_report(data, output_path):
    """Write aggregation report to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        # Bug 8: no default handler for date objects in daily_counts keys
        # This will raise TypeError: keys must be str, int, float, bool or None
        json.dump(data, f, indent=2)
''')

# === Generate log files ===
# Use .log for most but one .LOG file that gets missed (Bug 1)
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
"""

# This file has .LOG extension (uppercase) - missed by Bug 1
log3_content = """2024-03-16T14:00:00+00:00 payment-svc ERROR Duplicate transaction detected txn-8012
2024-03-16T14:01:00+00:00 auth-service INFO Database reconnected successfully
"""

with open("/app/logs/app-2024-03-15.log", "w") as f:
    f.write(log1_content.strip() + "\n")

with open("/app/logs/app-2024-03-16.log", "w") as f:
    f.write(log2_content.strip() + "\n")

# Bug 1 trigger: uppercase .LOG extension
with open("/app/logs/app-2024-03-16-late.LOG", "w") as f:
    f.write(log3_content.strip() + "\n")

print("Generated broken log aggregator at /app/logagg/")
print("Generated log files at /app/logs/")
