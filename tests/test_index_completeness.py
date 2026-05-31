"""Temporal index completeness tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "environment"))

from src.temporal_index import TemporalIndex
from src.compactor import IncrementalCompactor
from src.models import LogEntry


class TestIndexCompleteness:
    def test_all_entries_indexed(self):
        """Index must contain every input entry."""
        entries = [
            LogEntry(seq_id=i, timestamp=1000.0 + i * 0.5,
                     source_id="s", payload=f"m{i}")
            for i in range(1, 21)
        ]
        index = TemporalIndex()
        index.build(entries)
        assert index.count == 20, f"Expected 20, got {index.count}"

    def test_entries_with_same_timestamp_all_indexed(self):
        """Multiple entries at same timestamp must all be in the index."""
        entries = [
            LogEntry(seq_id=1, timestamp=100.0, source_id="a", payload="x"),
            LogEntry(seq_id=2, timestamp=100.0, source_id="b", payload="y"),
            LogEntry(seq_id=3, timestamp=100.0, source_id="c", payload="z"),
            LogEntry(seq_id=4, timestamp=101.0, source_id="a", payload="w"),
        ]
        index = TemporalIndex()
        index.build(entries)
        assert index.count == 4, f"Expected 4, got {index.count}"

    def test_range_query_includes_boundary_entries(self):
        """Range query [start, end] must include entries at boundaries."""
        entries = [
            LogEntry(seq_id=i, timestamp=float(i), source_id="s", payload=f"p{i}")
            for i in range(1, 11)
        ]
        index = TemporalIndex()
        index.build(entries)
        results = index.query_range(3.0, 7.0)
        assert len(results) == 5, f"Expected 5 entries in [3,7], got {len(results)}"

    def test_seq_lookup_all_entries(self):
        """Every entry must be findable by seq_id."""
        entries = [
            LogEntry(seq_id=i, timestamp=100.0 + i, source_id="s", payload=f"e{i}")
            for i in range(1, 16)
        ]
        index = TemporalIndex()
        index.build(entries)
        for e in entries:
            found = index.lookup_seq(e.seq_id)
            assert found is not None, f"seq_id {e.seq_id} not found"

    def test_compaction_index_matches_output(
        self, fresh_segments_dir, tmp_checkpoint_dir, tmp_output_dir
    ):
        """After compaction, index count must match output count."""
        compactor = IncrementalCompactor(
            segments_dir=fresh_segments_dir,
            checkpoint_dir=tmp_checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = compactor.run_compaction()
        assert output.entry_count > 0
        assert compactor.index.count == output.entry_count, (
            f"Index has {compactor.index.count} but output has "
            f"{output.entry_count} entries"
        )

    def test_same_timestamp_entries_all_queryable(self):
        """Range query at a shared timestamp must return all entries there."""
        entries = [
            LogEntry(seq_id=1, timestamp=5.0, source_id="a", payload="p1"),
            LogEntry(seq_id=2, timestamp=5.0, source_id="b", payload="p2"),
            LogEntry(seq_id=3, timestamp=5.0, source_id="c", payload="p3"),
        ]
        index = TemporalIndex()
        index.build(entries)
        results = index.query_range(5.0, 5.0)
        assert len(results) == 3, (
            f"Expected 3 entries at ts=5.0, got {len(results)}"
        )
