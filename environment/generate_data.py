#!/usr/bin/env python3
"""Generate interleaved cipher log data with two-layer obfuscation."""
import os
import struct
import json
import hashlib

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

CATEGORIES = [
    "auth", "network", "storage", "compute", "deploy",
    "monitor", "backup", "sync", "alert", "config"
]

ACTIONS = [
    "started", "completed", "failed", "retried", "timeout",
    "blocked", "resumed", "cancelled", "queued", "verified"
]

TARGETS = [
    "node-a", "node-b", "node-c", "node-d", "node-e",
    "node-f", "node-g", "node-h", "cluster", "gateway"
]


def make_record(seq_id):
    """Create a single 64-byte log record."""
    # Layout: [4B seq_id LE][8B category null-padded][48B message null-padded][4B zero padding]
    record = bytearray(64)

    # Sequence ID (4 bytes, little-endian)
    struct.pack_into('<I', record, 0, seq_id)

    # Category (8 bytes, null-padded)
    cat = CATEGORIES[seq_id % len(CATEGORIES)]
    cat_bytes = cat.encode('utf-8')[:8]
    record[4:4+len(cat_bytes)] = cat_bytes

    # Message (48 bytes, null-padded)
    action = ACTIONS[(seq_id * 3 + 1) % len(ACTIONS)]
    target = TARGETS[(seq_id * 7 + 2) % len(TARGETS)]
    ts_hash = hashlib.sha256(f"log-{seq_id}".encode()).hexdigest()[:12]
    msg = f"{action} {target} ts={seq_id*1000+500:08d} id={ts_hash}"
    msg_bytes = msg.encode('utf-8')[:48]
    record[12:12+len(msg_bytes)] = msg_bytes

    # Last 4 bytes: zero padding (already zero from bytearray init)
    return record


def rotate_left_byte(b, n):
    """Rotate a single byte left by n bits."""
    n = n % 8
    return ((b << n) | (b >> (8 - n))) & 0xFF


def rotate_right_byte(b, n):
    """Rotate a single byte right by n bits."""
    n = n % 8
    return ((b >> n) | (b << (8 - n))) & 0xFF


# Generate all 150 records
NUM_RECORDS = 150
records = []
for i in range(NUM_RECORDS):
    records.append(make_record(i))

# Save reference JSON
reference = []
for i, rec in enumerate(records):
    seq_id = struct.unpack_from('<I', rec, 0)[0]
    cat = rec[4:12].split(b'\x00')[0].decode('utf-8')
    msg = rec[12:60].split(b'\x00')[0].decode('utf-8')
    reference.append({"id": seq_id, "category": cat, "message": msg})

os.makedirs("/var/lib/tbench", exist_ok=True)
with open("/var/lib/tbench/.reference.json", "w") as f:
    json.dump(reference, f, indent=2)

# === LAYER 1: Byte-interleave adjacent record pairs ===
# Records are processed in pairs (0,1), (2,3), (4,5), ...
# Each pair produces a 128-byte interleaved block:
#   output[2*i] = recordA[i], output[2*i+1] = recordB[i] for i in 0..63
interleaved = bytearray()
for pair_idx in range(NUM_RECORDS // 2):
    rec_a = records[pair_idx * 2]
    rec_b = records[pair_idx * 2 + 1]
    block = bytearray(128)
    for i in range(64):
        block[2*i] = rec_a[i]
        block[2*i + 1] = rec_b[i]
    interleaved.extend(block)

# === LAYER 2: Positional bit-rotation on 8-byte chunks ===
# Each 8-byte chunk in the interleaved stream is rotated.
# rotation_amount for chunk at global index c = (c * 5 + 3) % 8
rotated = bytearray(len(interleaved))
num_chunks = len(interleaved) // 8
for c in range(num_chunks):
    rot = (c * 5 + 3) % 8
    for b in range(8):
        rotated[c*8 + b] = rotate_left_byte(interleaved[c*8 + b], rot)

# Write final obfuscated data
with open("/app/data/cipher_log.bin", "wb") as f:
    f.write(rotated)

print(f"Generated {NUM_RECORDS} records, {len(rotated)} bytes")
print(f"Reference saved to /var/lib/tbench/.reference.json")
