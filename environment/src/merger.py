"""
Segment Merger - merges entries from multiple WAL segments into a single
temporally-ordered stream using k-way merge.
"""
import heapq
from typing import List, Tuple
from .models import LogEntry, WALSegment


class SegmentMerger:
    """Merges multiple WAL segments into a single ordered stream."""

    def merge_segments(self, segments: List[WALSegment]) -> List[LogEntry]:
        """
        K-way merge of segment entries into a single temporally-ordered list.
        Equal timestamps are tiebroken by seq_id for deterministic output.
        """
        if not segments:
            return []

        # Heap entries: (timestamp, seq_id, seg_idx, entry_idx)
        heap: List[Tuple[float, int, int, int]] = []
        for seg_idx, segment in enumerate(segments):
            if segment.entries:
                e = segment.entries[0]
                heapq.heappush(heap, (e.timestamp, e.seq_id, seg_idx, 0))

        result = []
        while heap:
            _, _, seg_idx, entry_idx = heapq.heappop(heap)
            entry = segments[seg_idx].entries[entry_idx]
            result.append(entry)

            next_idx = entry_idx + 1
            if next_idx < len(segments[seg_idx].entries):
                ne = segments[seg_idx].entries[next_idx]
                heapq.heappush(heap, (ne.timestamp, ne.seq_id, seg_idx, next_idx))

        return result
