"""
Recovery Manager - coordinates crash recovery and output validation.
"""
import json
from pathlib import Path
from typing import List

from .models import CompactedOutput
from .compactor import IncrementalCompactor


class RecoveryManager:
    """Manages crash recovery for the compaction pipeline."""

    def __init__(
        self,
        segments_dir: Path,
        checkpoint_dir: Path,
        output_dir: Path,
        dedup_window: float = 5.0,
    ):
        self.segments_dir = segments_dir
        self.checkpoint_dir = checkpoint_dir
        self.output_dir = output_dir
        self.dedup_window = dedup_window

    def recover_and_compact(self) -> CompactedOutput:
        """Full recovery + compaction flow."""
        compactor = IncrementalCompactor(
            segments_dir=self.segments_dir,
            checkpoint_dir=self.checkpoint_dir,
            output_dir=self.output_dir,
            dedup_window=self.dedup_window,
        )
        compactor.load_checkpoint()
        output = compactor.run_compaction()
        if output.entries:
            compactor.save_checkpoint(output)
        return output

    def validate_output(self, output: CompactedOutput) -> List[str]:
        """Validate output consistency."""
        errors = []
        if not output.entries:
            return errors

        # Check monotonic seq_ids
        for i in range(1, len(output.entries)):
            if output.entries[i].seq_id <= output.entries[i - 1].seq_id:
                errors.append(
                    f"Non-monotonic seq_id at pos {i}: "
                    f"{output.entries[i].seq_id} <= {output.entries[i-1].seq_id}"
                )

        # Check monotonic timestamps
        for i in range(1, len(output.entries)):
            if output.entries[i].timestamp < output.entries[i - 1].timestamp:
                errors.append(
                    f"Non-monotonic timestamp at pos {i}: "
                    f"{output.entries[i].timestamp} < {output.entries[i-1].timestamp}"
                )

        return errors
