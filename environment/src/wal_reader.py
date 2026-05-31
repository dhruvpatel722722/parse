"""WAL Segment Reader - loads and validates segment files."""
import json
import zlib
from pathlib import Path
from typing import List

from .models import WALSegment, LogEntry


class WALReaderError(Exception):
    pass


class WALReader:
    """Reads WAL segments from disk."""

    def __init__(self, segments_dir: Path):
        self.segments_dir = segments_dir

    def load_all_segments(self) -> List[WALSegment]:
        """Load all segment files sorted by name."""
        if not self.segments_dir.exists():
            return []
        files = sorted(self.segments_dir.glob("segment_*.json"))
        segments = []
        for f in files:
            with open(f, "r") as fh:
                data = json.load(fh)
            seg = WALSegment.from_dict(data)
            self._validate(seg)
            segments.append(seg)
        return segments

    def _validate(self, segment: WALSegment) -> None:
        """Validate entry checksums."""
        for entry in segment.entries:
            if entry.checksum != 0:
                expected = zlib.crc32(entry.payload.encode()) & 0xFFFFFFFF
                if entry.checksum != expected:
                    raise WALReaderError(
                        f"Checksum mismatch in {segment.segment_id} "
                        f"entry {entry.seq_id}"
                    )
