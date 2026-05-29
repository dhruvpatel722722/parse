There's a broken Python log aggregation tool at `/app/logagg/`. It reads log files from `/app/logs/` and should produce a summary report at `/app/output/report.json`.

Run it with `python /app/logagg/main.py` — it crashes or produces wrong results. Your job is to find and fix all the bugs so it works correctly.

The tool has these components:
- `main.py` — orchestrator that reads config and drives the pipeline
- `parser.py` — parses individual log lines into structured records
- `aggregator.py` — groups records and computes statistics
- `writer.py` — formats and writes the JSON report

The report should contain:
```
{
  "total_events": <int>,
  "by_level": {"ERROR": <int>, "WARN": <int>, "INFO": <int>},
  "by_service": {"<name>": {"count": <int>, "error_rate": <float>}},
  "time_range": {"start": "<ISO-8601>", "end": "<ISO-8601>"},
  "multi_line_events": <int>,
  "daily_counts": {"<YYYY-MM-DD>": <int>}
}
```

Where `error_rate` is the fraction of ERROR events for that service (0.0 to 1.0). Times should be in UTC ISO-8601 format. Multi-line events (like stack traces) count as a single event. The `daily_counts` maps each calendar day to the number of events on that day.

The log files use standard syslog-like format:
```
2024-03-15T10:30:45+05:30 service-name ERROR Single line message
2024-03-15T10:30:46+05:30 service-name ERROR Exception occurred
  at module.function(file.py:42)
  at main.run(main.py:10)
```

Fix all bugs. The output file must exist at `/app/output/report.json` after running the fixed tool.
