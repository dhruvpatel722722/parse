"""Deduplication consistency tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "environment"))

from src.dedup_engine import DedupEngine
from src.compactor import IncrementalCompactor
from src.models import LogEntry


class TestDedupBoundary:
    def test_entries_at_exact_window_distance_are_duplicates(self):
        """Two entries with same key at exactly window_size apart are dups."""
        dedup = DedupEngine(window_size_seconds=5.0)
        entries = [
            LogEntry(seq_id=1, timestamp=100.0, source_id="s",
                     payload="msg"),
            LogEntry(seq_id=2, timestamp=105.0, source_id="s",
                     payload="msg"),
        ]
        result = dedup.process_entries(entries)
        assert len(result) == 1, f"Expected 1, got {len(result)}"

    def test_entries_just_beyond_window_are_not_duplicates(self):
        """Entries beyond the window must both survive."""
        dedup = DedupEngine(window_size_seconds=5.0)
        entries = [
            LogEntry(seq_id=1, timestamp=100.0, source_id="s",
                     payload="msg"),
            LogEntry(seq_id=2, timestamp=105.01, source_id="s",
                     payload="msg"),
        ]
        result = dedup.process_entries(entries)
        assert len(result) == 2

    def test_pipeline_dedup_catches_boundary_duplicate(
        self, fresh_segments_dir, tmp_checkpoint_dir, tmp_output_dir
    ):
        """Pipeline must catch the fixture's boundary duplicate."""
        compactor = IncrementalCompactor(
            segments_dir=fresh_segments_dir,
            checkpoint_dir=tmp_checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = compactor.run_compaction()

        # The fixture has exactly one duplicate pair at the boundary
        target = "listener bound to port 8080"
        matches = [e for e in output.entries if e.payload == target]
        assert len(matches) == 1, (
            f"Expected 1 copy of boundary duplicate, got {len(matches)}"
        )

    def test_different_sources_not_deduped(self):
        """Same payload from different sources must not be deduped."""
        dedup = DedupEngine(window_size_seconds=5.0)
        entries = [
            LogEntry(seq_id=1, timestamp=100.0, source_id="a", payload="x"),
            LogEntry(seq_id=2, timestamp=102.0, source_id="b", payload="x"),
        ]
        result = dedup.process_entries(entries)
        assert len(result) == 2

    def test_fresh_compaction_correct_count(
        self, fresh_segments_dir, tmp_checkpoint_dir, tmp_output_dir
    ):
        """Fresh compaction: 16 input entries minus 1 boundary dup = 15."""
        compactor = IncrementalCompactor(
            segments_dir=fresh_segments_dir,
            checkpoint_dir=tmp_checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = compactor.run_compaction()
        assert output.entry_count == 15, (
            f"Expected 15, got {output.entry_count} "
            f"(dropped={output.dropped_duplicates})"
        )
