"""
Incremental Compactor - orchestrates the full compaction pipeline.

Pipeline stages:
  1. Load checkpoint (if recovering)
  2. Load and filter WAL segments
  3. Handle partial segment resume
  4. Merge segments into temporal order
  5. Deduplicate
  6. Assign final sequence IDs
  7. Build temporal index
"""
import json
from pathlib import Path
from typing import Optional, List

from .models import LogEntry, WALSegment, Checkpoint, CompactedOutput
from .wal_reader import WALReader
from .dedup_engine import DedupEngine
from .merger import SegmentMerger
from .temporal_index import TemporalIndex


class IncrementalCompactor:
    """Orchestrates incremental log compaction."""

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

        self.reader = WALReader(segments_dir)
        self.dedup = DedupEngine(window_size_seconds=dedup_window)
        self.merger = SegmentMerger()
        self.index = TemporalIndex()

        self._checkpoint: Optional[Checkpoint] = None
        self._next_seq_id: int = 1

    def load_checkpoint(self) -> Optional[Checkpoint]:
        """Load checkpoint for recovery."""
        cp_path = self.checkpoint_dir / "latest.json"
        if not cp_path.exists():
            return None

        with open(cp_path, "r") as f:
            data = json.load(f)

        self._checkpoint = Checkpoint.from_dict(data)

        # Resume sequence numbering from checkpoint
        self._next_seq_id = self._checkpoint.last_seq_id + 1

        # Restore dedup engine state so we don't re-emit duplicates
        if self._checkpoint.dedup_window_state:
            self.dedup.restore_state(self._checkpoint.dedup_window_state)

        return self._checkpoint

    def run_compaction(self) -> CompactedOutput:
        """Execute one compaction round."""
        segments = self.reader.load_all_segments()
        if not segments:
            return CompactedOutput()

        # Filter out fully-processed segments
        to_process = self._filter_processed(segments)
        if not to_process:
            return CompactedOutput()

        # Handle partial segment resume
        to_process = self._apply_partial_resume(to_process)

        # Merge into temporal order
        merged = self.merger.merge_segments(to_process)

        # Deduplicate
        deduped = self.dedup.process_entries(merged)

        # Assign final sequence IDs
        output_entries = self._assign_seq_ids(deduped)

        # Build temporal index
        self.index.build(output_entries)

        return CompactedOutput(
            entries=output_entries,
            final_seq_id=self._next_seq_id - 1,
            entry_count=len(output_entries),
            dropped_duplicates=len(merged) - len(deduped),
            segments_consumed=[s.segment_id for s in to_process],
        )

    def _filter_processed(self, segments: List[WALSegment]) -> List[WALSegment]:
        """Remove segments that were fully processed before crash."""
        if not self._checkpoint:
            return segments
        done = set(self._checkpoint.segments_processed)
        return [s for s in segments if s.segment_id not in done]

    def _apply_partial_resume(self, segments: List[WALSegment]) -> List[WALSegment]:
        """Skip already-processed entries in the partial segment."""
        if not self._checkpoint or not self._checkpoint.partial_segment_id:
            return segments

        result = []
        for seg in segments:
            if seg.segment_id == self._checkpoint.partial_segment_id:
                offset = self._checkpoint.partial_offset
                remaining = seg.entries[offset:]
                if remaining:
                    result.append(WALSegment(
                        segment_id=seg.segment_id,
                        source_id=seg.source_id,
                        entries=remaining,
                        created_at=seg.created_at,
                        closed=seg.closed,
                    ))
            else:
                result.append(seg)
        return result

    def _assign_seq_ids(self, entries: List[LogEntry]) -> List[LogEntry]:
        """Assign monotonically increasing sequence IDs."""
        result = []
        for entry in entries:
            result.append(LogEntry(
                seq_id=self._next_seq_id,
                timestamp=entry.timestamp,
                source_id=entry.source_id,
                payload=entry.payload,
                checksum=entry.checksum,
            ))
            self._next_seq_id += 1
        return result

    def save_checkpoint(self, output: CompactedOutput) -> None:
        """Persist checkpoint."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        cp = Checkpoint(
            last_seq_id=output.final_seq_id,
            last_timestamp=output.entries[-1].timestamp if output.entries else 0.0,
            segments_processed=output.segments_consumed,
            dedup_window_state=self.dedup.get_state(),
        )
        with open(self.checkpoint_dir / "latest.json", "w") as f:
            json.dump(cp.to_dict(), f, indent=2)
