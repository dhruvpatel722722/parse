#!/usr/bin/env python3
"""Generate obfuscated telemetry archive with two interacting transformations."""
import os
import struct
import json
import random
import hashlib

random.seed(31415)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# Secret permutation for 13-byte blocks
PERM = [11, 10, 12, 3, 2, 5, 1, 6, 8, 0, 7, 4, 9]

# Secret XOR key (37 bytes, repeating)
XOR_KEY = bytes([252, 202, 25, 107, 59, 179, 9, 140, 238, 124, 221, 129, 131,
                 202, 106, 162, 220, 155, 139, 32, 161, 110, 142, 43, 10, 91,
                 122, 129, 222, 49, 115, 226, 50, 59, 65, 238, 0])

NODES = ["alpha-cluster", "beta-gateway", "gamma-worker", "delta-proxy",
         "epsilon-cache", "zeta-storage", "eta-compute", "theta-broker",
         "iota-monitor", "kappa-router", "lambda-queue", "mu-scheduler"]

CHANNELS = ["inbound", "outbound", "internal", "upstream", "downstream", "lateral"]

NUM_RECORDS = 250
FRAME_SIZE = 91
PERM_BLOCK = 13
XOR_KEY_LEN = 37

records = []
for i in range(NUM_RECORDS):
    frame = bytearray(FRAME_SIZE)
    struct.pack_into('<I', frame, 0, i)

    node = NODES[i % len(NODES)]
    chan = CHANNELS[(i * 5 + 2) % len(CHANNELS)]
    tag = hashlib.md5(f"d-{i}".encode()).hexdigest()[:8]
    f1 = f"{node}.{chan}.{tag}"
    f1_bytes = f1.encode('utf-8')[:40]
    frame[4:4+len(f1_bytes)] = f1_bytes

    val = (i * 17 + 3) % 10000
    ts = i * 500 + 1000000
    chk = hashlib.sha256(f"chk-{i}".encode()).hexdigest()[:12]
    f2 = f"val={val:04d}.{i%100:02d} ts={ts:010d} chk={chk}"
    f2_bytes = f2.encode('utf-8')[:44]
    frame[44:44+len(f2_bytes)] = f2_bytes

    records.append(frame)

# Save reference
reference = []
for frame in records:
    seq_id = struct.unpack_from('<I', frame, 0)[0]
    f1 = frame[4:44].split(b'\x00')[0].decode('utf-8')
    f2 = frame[44:88].split(b'\x00')[0].decode('utf-8')
    reference.append({"id": seq_id, "field1": f1, "field2": f2})

os.makedirs("/var/lib/tbench", exist_ok=True)
with open("/var/lib/tbench/.reference.json", "w") as f:
    json.dump(reference, f, indent=2)

# Serialize
raw = bytearray()
for frame in records:
    raw.extend(frame)

# Layer 1: Permutation on 13-byte blocks
permuted = bytearray(len(raw))
for block_start in range(0, len(raw), PERM_BLOCK):
    block = raw[block_start:block_start + PERM_BLOCK]
    for i in range(PERM_BLOCK):
        permuted[block_start + PERM[i]] = block[i]

# Layer 2: XOR with repeating key
xored = bytearray(len(permuted))
for i in range(len(permuted)):
    xored[i] = permuted[i] ^ XOR_KEY[i % XOR_KEY_LEN]

with open("/app/data/telemetry.bin", "wb") as f:
    f.write(xored)

print(f"Generated {NUM_RECORDS} records, {len(xored)} bytes")
