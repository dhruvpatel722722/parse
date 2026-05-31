"""Checkpoint recovery tests."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "environment"))

from src.compactor import IncrementalCompactor
from src.recovery import RecoveryManager


class TestRecovery:
    def test_sequence_ids_monotonically_increasing(
        self, segments_dir, checkpoint_dir, tmp_output_dir
    ):
        """Post-recovery seq_ids must be strictly monotonic."""
        compactor = IncrementalCompactor(
            segments_dir=segments_dir,
            checkpoint_dir=checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        compactor.load_checkpoint()
        output = compactor.run_compaction()
        assert len(output.entries) > 0

        for i in range(1, len(output.entries)):
            assert output.entries[i].seq_id == output.entries[i-1].seq_id + 1, (
                f"Gap at pos {i}: {output.entries[i].seq_id} vs "
                f"prev {output.entries[i-1].seq_id}"
            )

    def test_recovery_seq_above_all_previously_emitted(
        self, segments_dir, checkpoint_dir, tmp_output_dir
    ):
        """
        After crash recovery, new sequence IDs must not conflict
        with any IDs that were assigned before the crash.
        """
        cp_path = checkpoint_dir / "latest.json"
        with open(cp_path) as f:
            cp = json.load(f)

        # Compute the highest seq_id that could have been emitted
        # before the crash, accounting for all processing stages
        high_water = cp["last_seq_id"] + cp.get("partial_offset", 0)

        compactor = IncrementalCompactor(
            segments_dir=segments_dir,
            checkpoint_dir=checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        compactor.load_checkpoint()
        output = compactor.run_compaction()
        assert len(output.entries) > 0

        first_new = output.entries[0].seq_id
        assert first_new > high_water, (
            f"Seq_id conflict: first new ID ({first_new}) overlaps with "
            f"pre-crash range (high_water={high_water})"
        )

    def test_recovery_manager_validates_clean(
        self, segments_dir, checkpoint_dir, tmp_output_dir
    ):
        """Full recovery flow must produce zero validation errors."""
        manager = RecoveryManager(
            segments_dir=segments_dir,
            checkpoint_dir=checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = manager.recover_and_compact()
        assert len(output.entries) > 0
        errors = manager.validate_output(output)
        assert not errors, f"Validation errors: {errors}"
