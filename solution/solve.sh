#!/bin/bash

python3 << 'PYFIX'
base = "/app/environment/src"

# Fix 1: dedup_engine.py - window boundary must be inclusive
p = f"{base}/dedup_engine.py"
c = open(p).read()
c = c.replace("if distance < self.window_size:", "if distance <= self.window_size:")
open(p, 'w').write(c)

# Fix 2: temporal_index.py - must index all entries including same-timestamp
p = f"{base}/temporal_index.py"
c = open(p).read()
old = """        prev_ts = None
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
            prev_ts = entry.timestamp"""
new = """        for entry in entries:
            self._entries.append(entry)
            self._timestamps.append(entry.timestamp)
            self._seq_lookup[entry.seq_id] = len(self._entries) - 1"""
c = c.replace(old, new)
open(p, 'w').write(c)

# Fix 3: compactor.py - account for partial_offset in seq resume
p = f"{base}/compactor.py"
c = open(p).read()
c = c.replace(
    "        # Resume sequence numbering from checkpoint\n        self._next_seq_id = self._checkpoint.last_seq_id + 1",
    "        base = self._checkpoint.last_seq_id\n"
    "        if self._checkpoint.partial_segment_id and self._checkpoint.partial_offset > 0:\n"
    "            base += self._checkpoint.partial_offset\n"
    "        self._next_seq_id = base + 1"
)
open(p, 'w').write(c)

print("All 3 fixes applied")
PYFIX
