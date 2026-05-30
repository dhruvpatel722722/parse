#!/usr/bin/env python3
"""Generate encoded sensor log with two-layer obfuscation.
Layer 1: XOR with 24-byte repeating key
Layer 2: Permutation on 12-byte blocks
"""
import os
import struct
import json
import random
import hashlib

random.seed(77777)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# XOR key (24 bytes)
XOR_KEY = bytes([0x7C, 0xA3, 0x15, 0xE8, 0x4F, 0xD2, 0x96, 0x3B,
                 0x81, 0x57, 0xCE, 0x2A, 0xF4, 0x69, 0x0D, 0xB8,
                 0x43, 0xE1, 0x7F, 0x26, 0x9A, 0x5D, 0xC0, 0x34])

# Permutation for 12-byte blocks
PERM = [7, 2, 10, 4, 11, 1, 8, 0, 5, 9, 3, 6]

SENSORS = ["temp-A1", "temp-A2", "temp-B1", "pressure-B3", "pressure-C1",
           "humidity-C2", "humidity-D1", "flow-E1", "flow-E2", "vibration-F1"]

records = []
for i in range(300):
    sensor = SENSORS[i % len(SENSORS)]
    day = (i // 24) + 1
    hour = i % 24
    minute = (i * 7) % 60
    ts = f"2024-03-{day:02d}T{hour:02d}:{minute:02d}:00Z"
    value = round(random.uniform(5.0, 950.0), 4)
    records.append({"seq": i, "sensor": sensor, "timestamp": ts, "value": value})

# Serialize to 64-byte frames
frames = bytearray()
for rec in records:
    frame = bytearray(64)
    struct.pack_into('<I', frame, 0, rec["seq"])
    name = rec["sensor"].encode()[:16]
    frame[4:4+len(name)] = name
    ts = rec["timestamp"].encode()[:24]
    frame[20:20+len(ts)] = ts
    struct.pack_into('<d', frame, 44, rec["value"])
    frames.extend(frame)

# Layer 1: XOR
xored = bytearray(len(frames))
for i in range(len(frames)):
    xored[i] = frames[i] ^ XOR_KEY[i % 24]

# Layer 2: Permute 12-byte blocks
permuted = bytearray(len(xored))
for block_start in range(0, len(xored), 12):
    block = xored[block_start:block_start+12]
    if len(block) < 12:
        permuted[block_start:block_start+len(block)] = block
        continue
    for i in range(12):
        permuted[block_start + PERM[i]] = block[i]

with open("/app/data/sensorlog.dat", "wb") as f:
    f.write(permuted)

os.makedirs("/var/lib/tbench", exist_ok=True)
with open("/var/lib/tbench/.reference.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Generated {len(records)} records, {len(permuted)} bytes")
