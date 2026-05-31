#!/usr/bin/env python3
"""Generate the corrupted sensor log binary file and reference output."""
import json
import os
import struct
import random

random.seed(77777)

os.makedirs("/app/data", exist_ok=True)

NUM_FRAMES = 300
FRAME_SIZE = 64
XOR_KEY_LEN = 192  # 3 frames

# --- Generate sensor data ---
sensor_types = ["temp", "pressure", "humidity", "flow", "vibration"]
letters = "ABCDEF"
digits = "123456789"

records = []
for i in range(NUM_FRAMES):
    stype = random.choice(sensor_types)
    letter = random.choice(letters)
    digit = random.choice(digits)
    sensor_name = f"{stype}-{letter}{digit}"

    day = random.randint(1, 31)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    timestamp = f"2024-03-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"

    value = round(random.uniform(5.0, 950.0), 4)

    records.append({
        "seq": i,
        "sensor": sensor_name,
        "timestamp": timestamp,
        "value": value
    })

# --- Build raw frames ---
# Frame format (64 bytes):
# [0-3]   uint32 LE: sequence number (0-299)
# [4-15]  ASCII null-padded: sensor name (12 bytes)
# [16-39] ASCII null-padded: timestamp (24 bytes)
# [40-47] float64 LE: sensor value
# [48-63] zero padding (16 bytes)
raw_frames = bytearray()
for rec in records:
    frame = bytearray(FRAME_SIZE)
    struct.pack_into('<I', frame, 0, rec["seq"])
    sensor_bytes = rec["sensor"].encode('ascii')
    frame[4:4+len(sensor_bytes)] = sensor_bytes
    ts_bytes = rec["timestamp"].encode('ascii')
    frame[16:16+len(ts_bytes)] = ts_bytes
    struct.pack_into('<d', frame, 40, rec["value"])
    raw_frames.extend(frame)

# --- Generate permutation (fixed, random) ---
perm = list(range(FRAME_SIZE))
random.shuffle(perm)

# --- Generate XOR key (192 bytes, random, no zero bytes) ---
xor_key = bytes([random.randint(1, 255) for _ in range(XOR_KEY_LEN)])

# --- Apply corruption: first permute each frame, then XOR ---
permuted = bytearray()
for i in range(NUM_FRAMES):
    offset = i * FRAME_SIZE
    frame = raw_frames[offset:offset + FRAME_SIZE]
    permuted_frame = bytearray(FRAME_SIZE)
    for dst, src in enumerate(perm):
        permuted_frame[dst] = frame[src]
    permuted.extend(permuted_frame)

# Apply XOR over entire permuted data
corrupted = bytearray(len(permuted))
for i in range(len(permuted)):
    corrupted[i] = permuted[i] ^ xor_key[i % XOR_KEY_LEN]

# --- Write corrupted binary ---
with open('/app/data/sensorlog.dat', 'wb') as f:
    f.write(bytes(corrupted))

# --- Write reference JSON (for test verification) ---
reference_path = "/var/lib/tbench/.reference.json"
os.makedirs(os.path.dirname(reference_path), exist_ok=True)
with open(reference_path, 'w') as f:
    json.dump(records, f, indent=2)

print(f"Generated {NUM_FRAMES} corrupted frames -> /app/data/sensorlog.dat")
print(f"Reference output -> {reference_path}")
print(f"File size: {len(corrupted)} bytes")
