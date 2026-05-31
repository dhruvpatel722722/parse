# Fix Log Aggregation Pipeline

## Background

A distributed log aggregation pipeline ingests entries from multiple source nodes via WAL segments and compacts them into a unified, deduplicated, temporally-ordered output. The pipeline recently started producing incorrect output after a refactoring.

## Symptoms

1. **Ordering anomalies** — entries from different sources that share the same timestamp appear in non-deterministic order
2. **Duplicate entries** — certain entries that should be caught by the dedup window are leaking through
3. **Incomplete index** — range queries on the temporal index return fewer entries than expected
4. **Sequence conflicts after crash recovery** — when resuming from a checkpoint, new sequence IDs overlap with previously emitted entries

## System Layout

Source code is in `/app/environment/src/`:
- `models.py` — Data structures (LogEntry, WALSegment, Checkpoint, CompactedOutput)
- `wal_reader.py` — Loads WAL segment files from disk
- `merger.py` — K-way merge of segments into temporal order
- `dedup_engine.py` — Sliding-window deduplication
- `temporal_index.py` — Time-based index for range queries
- `compactor.py` — Orchestrates the full compaction pipeline
- `recovery.py` — Crash recovery coordination

Fixtures in `/app/environment/fixtures/` contain WAL segments from three source nodes with overlapping time ranges, plus a checkpoint representing an interrupted partial compaction.

## Running Tests

```bash
cd /app && pytest tests/ -v
```
