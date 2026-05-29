#!/usr/bin/env python3
"""Generate scrambled database dump with two-layer obfuscation."""
import os
import struct
import json
import random
import hashlib

random.seed(12345)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# Secret permutation for 16-byte blocks
PERM = [11, 3, 14, 7, 0, 9, 5, 13, 2, 10, 6, 15, 8, 4, 1, 12]

# Secret XOR key (32 bytes, repeating)
XOR_KEY = bytes([0x5A, 0x3F, 0xC1, 0x87, 0x2E, 0x94, 0xD6, 0x1B,
                 0xA8, 0x73, 0x4D, 0xF2, 0x69, 0xB5, 0x0E, 0xE7,
                 0x31, 0xCC, 0x56, 0xAA, 0x7F, 0x18, 0xE3, 0x42,
                 0x9D, 0x64, 0xBB, 0x05, 0xF8, 0x2C, 0x71, 0xD9])

WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
         "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi",
         "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
         "config", "server", "client", "cache", "queue", "index", "route", "token"]

records = []
for i in range(200):
    prefix = WORDS[i % len(WORDS)]
    suffix = WORDS[(i * 7 + 3) % len(WORDS)]
    key = f"{prefix}.{suffix}.{i:03d}"
    
    val_words = [WORDS[(i * 11 + j * 5) % len(WORDS)] for j in range(4)]
    value = f"data={'.'.join(val_words)} seq={i:04d} hash={hashlib.md5(str(i).encode()).hexdigest()[:8]}"
    
    records.append({"id": i, "key": key, "value": value})

# Serialize to fixed-width frames
frames = bytearray()
for rec in records:
    frame = bytearray(128)
    struct.pack_into('<I', frame, 0, rec["id"])
    key_bytes = rec["key"].encode("utf-8")[:32]
    frame[4:4+len(key_bytes)] = key_bytes
    val_bytes = rec["value"].encode("utf-8")[:92]
    frame[36:36+len(val_bytes)] = val_bytes
    frames.extend(frame)

# Layer 1: Apply permutation to each 16-byte block
permuted = bytearray(len(frames))
for block_start in range(0, len(frames), 16):
    block = frames[block_start:block_start+16]
    for i in range(16):
        permuted[block_start + PERM[i]] = block[i]

# Layer 2: XOR each byte with position-derived key
xored = bytearray(len(permuted))
for i in range(len(permuted)):
    xored[i] = permuted[i] ^ XOR_KEY[i % len(XOR_KEY)]

# Write final scrambled data
with open("/app/data/records.dat", "wb") as f:
    f.write(xored)

# Write reference for testing
with open("/app/data/.reference.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Generated {len(records)} records, {len(xored)} bytes")
