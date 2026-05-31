"""
Temporal Index - provides time-range queries over compacted entries.

Assumes entries are added in timestamp order (as produced by the merger).
Supports efficient range lookups using binary search.
"""
from typing import List, Optional, Tuple, Dict
from bisect import bisect_left, bisect_right
from .models import LogEntry


class TemporalIndex:
    """Time-ordered index over log entries."""

    def __init__(self):
        self._entries: List[LogEntry] = []
        self._timestamps: List[float] = []
        self._seq_lookup: Dict[int, int] = {}

    def build(self, entries: List[LogEntry]) -> None:
        """
        Build index from ordered entries. Entries must be pre-sorted
        by timestamp. Constructs internal lookup structures.
        """
        self._entries = []
        self._timestamps = []
        self._seq_lookup = {}

        prev_ts = None
        for entry in entries:
            # Maintain strictly increasing timestamp index for binary search.
            # Skip entries at same timestamp to keep index monotonic.
            if prev_ts is not None and entry.timestamp == prev_ts:
                # Still record in seq lookup for direct access
                self._seq_lookup[entry.seq_id] = len(self._entries) - 1
                continue
            self._entries.append(entry)
            self._timestamps.append(entry.timestamp)
            self._seq_lookup[entry.seq_id] = len(self._entries) - 1
            prev_ts = entry.timestamp

    def query_range(self, start_ts: float, end_ts: float) -> List[LogEntry]:
        """Return entries with timestamp in [start_ts, end_ts]."""
        lo = bisect_left(self._timestamps, start_ts)
        hi = bisect_right(self._timestamps, end_ts)
        return self._entries[lo:hi]

    def lookup_seq(self, seq_id: int) -> Optional[LogEntry]:
        """Find entry by sequence ID."""
        pos = self._seq_lookup.get(seq_id)
        if pos is None:
            return None
        if pos < len(self._entries):
            return self._entries[pos]
        return None

    @property
    def count(self) -> int:
        return len(self._entries)

    def get_time_bounds(self) -> Tuple[float, float]:
        if not self._timestamps:
            return (0.0, 0.0)
        return (self._timestamps[0], self._timestamps[-1])
