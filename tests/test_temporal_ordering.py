"""Temporal ordering invariant tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "environment"))

from src.merger import SegmentMerger
from src.compactor import IncrementalCompactor
from src.models import LogEntry, WALSegment


class TestMergeOrdering:
    def test_cross_source_temporal_monotonicity(self, loaded_segments):
        """Merged output must be temporally monotonic."""
        merger = SegmentMerger()
        merged = merger.merge_segments(loaded_segments)

        for i in range(1, len(merged)):
            assert merged[i].timestamp >= merged[i - 1].timestamp, (
                f"Position {i}: ts={merged[i].timestamp} < "
                f"prev={merged[i-1].timestamp}"
            )

    def test_full_compaction_temporal_order(
        self, fresh_segments_dir, tmp_checkpoint_dir, tmp_output_dir
    ):
        """Full pipeline output must maintain temporal monotonicity."""
        compactor = IncrementalCompactor(
            segments_dir=fresh_segments_dir,
            checkpoint_dir=tmp_checkpoint_dir,
            output_dir=tmp_output_dir,
        )
        output = compactor.run_compaction()
        assert len(output.entries) > 0

        for i in range(1, len(output.entries)):
            assert output.entries[i].timestamp >= output.entries[i-1].timestamp
