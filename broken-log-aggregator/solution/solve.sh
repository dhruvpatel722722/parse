#!/bin/bash
# Fix all bugs in the log aggregator

# Bug 1: Fix variable name typo in main.py (result -> results)
sed -i 's/write_report(result,/write_report(results,/' /app/logagg/main.py

# Bug 2: Fix regex in parser.py to handle timezone with colon (+05:30)
sed -i 's/\[+-\]\\d{4}/[+-]\\d{2}:\\d{2}/' /app/logagg/parser.py

# Bug 3: Fix inverted multiline condition (not line.startswith -> line.startswith)
sed -i 's/elif current_record and not line.startswith(" ")/elif current_record and line.startswith(" ")/' /app/logagg/parser.py

# Bug 4: Fix date format in aggregator.py (%Y-%d-%m -> %Y-%m-%d)
sed -i 's/%Y-%d-%m/%Y-%m-%d/' /app/logagg/aggregator.py

# Bug 5: Fix error_rate calculation (divide by service count, not total)
sed -i 's/data\["errors"\] \/ total_events/data["errors"] \/ data["count"]/' /app/logagg/aggregator.py

# Bug 6: Fix file open mode in writer.py ("a" -> "w")
sed -i 's/open(output_path, "a")/open(output_path, "w")/' /app/logagg/writer.py

# Run the fixed tool
python /app/logagg/main.py
