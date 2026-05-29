#!/usr/bin/env python3
"""Generate scrambled database dump.

The scrambling applies a fixed 16-byte block permutation to the serialized data.
The permutation is non-trivial and must be reverse-engineered from the data patterns.
"""
import os
import struct
import json
import random
import hashlib

random.seed(12345)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# The secret permutation (applied to each 16-byte block)
# This maps: output[PERM[i]] = input[i]
# So to reverse: recovered[i] = scrambled[PERM[i]]
PERM = [11, 3, 14, 7, 0, 9, 5, 13, 2, 10, 6, 15, 8, 4, 1, 12]

# Generate 200 records with predictable but varied content
WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
         "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi",
         "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
         "config", "server", "client", "cache", "queue", "index", "route", "token"]

records = []
for i in range(200):
    # Keys are structured: "prefix.suffix" pattern
    prefix = WORDS[i % len(WORDS)]
    suffix = WORDS[(i * 7 + 3) % len(WORDS)]
    key = f"{prefix}.{suffix}.{i:03d}"
    
    # Values are structured strings with varying content
    val_words = [WORDS[(i * 11 + j * 5) % len(WORDS)] for j in range(4)]
    value = f"data={'.'.join(val_words)} seq={i:04d} hash={hashlib.md5(str(i).encode()).hexdigest()[:8]}"
    
    records.append({"id": i, "key": key, "value": value})

# Serialize to fixed-width frames
frames = bytearray()
for rec in records:
    frame = bytearray(128)
    # 4 bytes: little-endian id
    struct.pack_into('<I', frame, 0, rec["id"])
    # 32 bytes: null-padded key
    key_bytes = rec["key"].encode("utf-8")[:32]
    frame[4:4+len(key_bytes)] = key_bytes
    # 92 bytes: null-padded value  
    val_bytes = rec["value"].encode("utf-8")[:92]
    frame[36:36+len(val_bytes)] = val_bytes
    frames.extend(frame)

# Apply the permutation to each 16-byte block
scrambled = bytearray(len(frames))
for block_start in range(0, len(frames), 16):
    block = frames[block_start:block_start+16]
    for i in range(16):
        scrambled[block_start + PERM[i]] = block[i]

# Write scrambled data
with open("/app/data/records.dat", "wb") as f:
    f.write(scrambled)

# Write reference answer (for oracle verification)
with open("/app/data/.reference.json", "w") as f:
    json.dump(records, f, indent=2)

# Write permutation hash for anti-cheat (don't expose the actual permutation)
perm_hash = hashlib.sha256(str(PERM).encode()).hexdigest()[:16]
with open("/app/data/.perm_hash", "w") as f:
    f.write(perm_hash)

print(f"Generated {len(records)} records")
print(f"Frame size: 128 bytes, Total: {len(frames)} bytes")
print(f"Scrambled file: {len(scrambled)} bytes ({len(scrambled)//16} blocks)")
