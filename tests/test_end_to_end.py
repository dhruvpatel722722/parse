"""End-to-end integration tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "environment"))

from src.compactor import IncrementalCompactor
from src.recovery import RecoveryManager


class TestEndToEnd:
    def test_all_invariants_combined(
        self, fresh_segments_dir, tmp_checkpoint_dir, tmp_output_dir
    ):
        """All pipeline invariants must hold simultaneously."""
        compactor = IncrementalCompactor(
            segments_dir=fresh_segments_dir,
            checkpoint_dir=tmp_checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = compactor.run_compaction()
        entries = output.entries
        assert len(entries) > 0

        errors = []

        # Temporal monotonicity
        for i in range(1, len(entries)):
            if entries[i].timestamp < entries[i-1].timestamp:
                errors.append(f"ts violation at {i}")

        # Sequence monotonicity
        for i in range(1, len(entries)):
            if entries[i].seq_id != entries[i-1].seq_id + 1:
                errors.append(f"seq gap at {i}")

        # No within-window duplicates
        for i in range(len(entries)):
            for j in range(i+1, len(entries)):
                if entries[j].timestamp - entries[i].timestamp > 5.0:
                    break
                if (entries[i].source_id == entries[j].source_id and
                        entries[i].payload == entries[j].payload):
                    errors.append(f"dup at ({i},{j})")

        # Index completeness
        if compactor.index.count != len(entries):
            errors.append(
                f"index: {compactor.index.count} vs {len(entries)} entries"
            )

        assert not errors, f"Invariant violations: {errors}"

    def test_unique_data_preserved(
        self, fresh_segments_dir, tmp_checkpoint_dir, tmp_output_dir
    ):
        """All unique (source, payload) pairs must survive compaction."""
        from src.wal_reader import WALReader

        reader = WALReader(fresh_segments_dir)
        segments = reader.load_all_segments()
        input_unique = set()
        for seg in segments:
            for e in seg.entries:
                input_unique.add((e.source_id, e.payload))

        compactor = IncrementalCompactor(
            segments_dir=fresh_segments_dir,
            checkpoint_dir=tmp_checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = compactor.run_compaction()
        output_unique = {(e.source_id, e.payload) for e in output.entries}

        missing = input_unique - output_unique
        assert not missing, f"Lost data: {missing}"

    def test_recovery_full_validation(
        self, segments_dir, checkpoint_dir, tmp_output_dir
    ):
        """Recovery flow must produce valid, consistent output."""
        manager = RecoveryManager(
            segments_dir=segments_dir,
            checkpoint_dir=checkpoint_dir,
            output_dir=tmp_output_dir,
            dedup_window=5.0,
        )
        output = manager.recover_and_compact()
        errors = manager.validate_output(output)
        assert not errors, f"Recovery validation: {errors}"
