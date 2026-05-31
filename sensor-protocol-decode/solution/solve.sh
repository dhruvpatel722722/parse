#!/bin/bash
mkdir -p /app/output
cat > /app/extract.py << 'PYEOF'
"""
Sensor Protocol Decoder.
Decodes corrupted binary sensor log by reversing XOR cipher and byte permutation.
The XOR key and permutation were derived through structural cryptanalysis:
- Identified seq byte 0 column via XOR-diff fingerprinting (unique diff pattern)
- Used constant-source columns (zero padding, timestamp prefix) to recover key positions
- Matched all 64 columns to source positions via unique diff signatures across 300 frames
- Recovered full 192-byte key from known plaintext at deterministic positions
"""
import struct
import json
import os

os.makedirs("/app/output", exist_ok=True)

FRAME_SIZE = 64
NUM_FRAMES = 300
KEY_LEN = 192

# XOR key (192 bytes) recovered through known-plaintext cryptanalysis
XOR_KEY = bytes([
    80, 198, 73, 147, 37, 95, 85, 174, 123, 135, 203, 95, 116, 96, 231, 166,
    112, 124, 210, 242, 72, 36, 189, 175, 111, 15, 56, 45, 155, 180, 39, 254,
    159, 116, 65, 158, 136, 2, 77, 246, 195, 145, 150, 183, 6, 92, 219, 193,
    59, 82, 89, 158, 6, 101, 187, 69, 196, 233, 234, 219, 150, 73, 170, 19,
    214, 234, 191, 2, 240, 87, 74, 33, 83, 76, 137, 173, 70, 218, 142, 177,
    86, 37, 163, 1, 74, 81, 56, 224, 244, 76, 190, 36, 234, 233, 157, 223,
    252, 161, 184, 222, 211, 96, 47, 145, 136, 247, 23, 14, 132, 177, 241, 40,
    73, 67, 150, 244, 148, 83, 240, 186, 12, 139, 44, 236, 247, 125, 226, 41,
    102, 12, 233, 25, 168, 128, 143, 88, 153, 81, 54, 25, 224, 14, 32, 151,
    3, 4, 125, 75, 147, 46, 11, 32, 83, 39, 108, 169, 39, 96, 221, 163,
    54, 68, 28, 4, 187, 127, 196, 94, 130, 22, 121, 94, 235, 155, 186, 118,
    9, 228, 158, 120, 204, 205, 208, 6, 53, 77, 51, 95, 228, 123, 23, 15
])

# Byte permutation recovered through differential analysis of XOR-diff signatures.
# PERM[d] = source position whose byte appears at destination position d after permutation.
PERM = [
    36, 19, 17, 2, 31, 60, 32, 5, 40, 0, 53, 54, 51, 3, 55, 28,
    49, 44, 23, 57, 62, 15, 61, 48, 6, 37, 63, 25, 46, 12, 39, 58,
    34, 24, 26, 20, 18, 4, 30, 13, 50, 9, 16, 43, 33, 22, 11, 56,
    47, 45, 42, 27, 41, 14, 1, 29, 52, 7, 38, 35, 8, 59, 10, 21
]

with open("/app/data/sensorlog.dat", "rb") as f:
    data = bytearray(f.read())

assert len(data) == NUM_FRAMES * FRAME_SIZE

# Decode all frames
records = []
for i in range(NUM_FRAMES):
    frame_start = i * FRAME_SIZE

    # Step 1: Undo XOR (key repeats every 192 bytes)
    permuted = bytearray(FRAME_SIZE)
    for d in range(FRAME_SIZE):
        key_pos = (i * FRAME_SIZE + d) % KEY_LEN
        permuted[d] = data[frame_start + d] ^ XOR_KEY[key_pos]

    # Step 2: Undo permutation (PERM[d] = source position at dest d)
    original = bytearray(FRAME_SIZE)
    for d in range(FRAME_SIZE):
        original[PERM[d]] = permuted[d]

    # Step 3: Parse frame fields
    seq = struct.unpack_from('<I', original, 0)[0]
    sensor = original[4:16].split(b'\x00')[0].decode('ascii')
    timestamp = original[16:40].split(b'\x00')[0].decode('ascii')
    value = round(struct.unpack_from('<d', original, 40)[0], 4)

    records.append({
        "seq": seq,
        "sensor": sensor,
        "timestamp": timestamp,
        "value": value
    })

# Sort by sequence number
records.sort(key=lambda r: r["seq"])

# Validate
assert len(records) == 300
assert records[0]["seq"] == 0
assert records[-1]["seq"] == 299

# Write output
with open("/app/output/readings.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Successfully decoded {len(records)} sensor readings.")
PYEOF

python /app/extract.py
