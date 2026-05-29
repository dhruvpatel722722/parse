#!/bin/bash
# Fix all bugs in the log aggregator

# Bug 1: Fix glob pattern to match both .log and .LOG extensions
cat > /tmp/fix_main.py << 'EOF'
import re

with open("/app/logagg/main.py", "r") as f:
    content = f.read()

# Replace the discover_logs function to handle case-insensitive matching
old = '''def discover_logs(directory):
    """Find all log files in directory."""
    # Bug 1: only matches .log not .LOG — misses some files
    pattern = os.path.join(directory, "*.log")
    return sorted(glob.glob(pattern))'''

new = '''def discover_logs(directory):
    """Find all log files in directory."""
    files = []
    for f in os.listdir(directory):
        if f.lower().endswith(".log"):
            files.append(os.path.join(directory, f))
    return sorted(files)'''

content = content.replace(old, new)

with open("/app/logagg/main.py", "w") as f:
    f.write(content)
EOF
python /tmp/fix_main.py

# Bug 3: Fix multiline detection (tab -> space)
sed -i 's/line.startswith("\\t")/line.startswith(" ")/' /app/logagg/parser.py

# Bug 4: Fix timezone conversion (should subtract offset to get UTC)
cat > /tmp/fix_parser.py << 'EOF'
with open("/app/logagg/parser.py", "r") as f:
    content = f.read()

old = '''    utc_dt = dt_naive + timedelta(hours=sign * offset_hours, minutes=sign * offset_minutes)'''
new = '''    utc_dt = dt_naive - timedelta(hours=sign * offset_hours, minutes=sign * offset_minutes)'''

content = content.replace(old, new)

with open("/app/logagg/parser.py", "w") as f:
    f.write(content)
EOF
python /tmp/fix_parser.py

# Bug 5: Fix daily_counts to use string key instead of date object
sed -i 's/day_key = rec\["timestamp"\].date()/day_key = rec["timestamp"].strftime("%Y-%m-%d")/' /app/logagg/aggregator.py

# Bug 6: Fix error_rate precision (round to 4 decimals)
sed -i 's/round(data\["errors"\] \/ data\["count"\], 2)/round(data["errors"] \/ data["count"], 4)/' /app/logagg/aggregator.py

# Bug 8: writer.py doesn't need fixing now since daily_counts keys are strings after bug 5 fix
# But we need to verify it works

# Run the fixed tool
python /app/logagg/main.py
