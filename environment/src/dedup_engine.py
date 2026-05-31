"""
Deduplication Engine - sliding window deduplication over log entries.

Removes duplicate entries that share the same source and payload content
within a configurable time window.
"""
import zlib
from typing import List, Dict, Tuple
from .models import LogEntry


class DedupEngine:
    """Sliding-window deduplication."""

    def __init__(self, window_size_seconds: float = 5.0):
        self.window_size = window_size_seconds
        # key -> list of timestamps where this key was seen
        self._seen: Dict[Tuple[str, int], List[float]] = {}

    def process_entries(self, entries: List[LogEntry]) -> List[LogEntry]:
        """Remove duplicates, return non-duplicate entries."""
        result = []
        for entry in entries:
            if not self._is_duplicate(entry):
                result.append(entry)
                self._record(entry)
        return result

    def _is_duplicate(self, entry: LogEntry) -> bool:
        """Check if entry duplicates a recent entry within the window."""
        key = self._make_key(entry)
        if key not in self._seen:
            return False

        for seen_ts in self._seen[key]:
            distance = abs(entry.timestamp - seen_ts)
            if distance < self.window_size:
                return True
        return False

    def _record(self, entry: LogEntry) -> None:
        """Record entry in the window."""
        key = self._make_key(entry)
        if key not in self._seen:
            self._seen[key] = []
        self._seen[key].append(entry.timestamp)
        # Evict entries outside 2x window (can never match anything new)
        cutoff = entry.timestamp - self.window_size * 2
        self._seen[key] = [t for t in self._seen[key] if t >= cutoff]

    def _make_key(self, entry: LogEntry) -> Tuple[str, int]:
        """Generate dedup key from source and payload content."""
        content_hash = zlib.crc32(entry.payload.encode()) & 0xFFFFFFFF
        return (entry.source_id, content_hash)

    def get_state(self) -> dict:
        """Serialize state for checkpointing."""
        return {f"{k[0]}|{k[1]}": v for k, v in self._seen.items()}

    def restore_state(self, state: dict) -> None:
        """Restore from checkpoint state."""
        self._seen = {}
        for key_str, timestamps in state.items():
            parts = key_str.split("|", 1)
            if len(parts) == 2:
                self._seen[(parts[0], int(parts[1]))] = timestamps
