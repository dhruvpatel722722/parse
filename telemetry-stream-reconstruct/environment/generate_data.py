#!/usr/bin/env python3
"""
Generate obfuscated telemetry stream data.

Each frame is 64 bytes of plaintext, transformed by:
  1. A fixed 16-byte block permutation (applied to each 16-byte chunk)
  2. A 32-byte XOR key (applied cyclically across the 64-byte frame)

Plaintext frame layout (64 bytes):
  [0:16]  - Header: 16 bytes, each derived from frame sequence number
            byte[i] = (seq * multiplier[i] + offset[i]) % 256
            multipliers: [1,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53]
            offsets:     [0,100,200,50,150,75,125,175,225,25,60,90,110,130,160,190]
  [16:48] - Sensor payload (pseudorandom)
  [48:64] - Zero padding (16 null bytes = one full block)

The 16 header bytes each have a unique linear relationship to the
sequence number, so every byte position in the header block has a
distinct XOR-difference fingerprint across frames.

Permutation: out[i] = block[perm[i]]
XOR key: final[i] = permuted[i] ^ key[i % 32]

Outputs:
  /app/telemetry.bin            - 300 encrypted frames (19200 bytes)
  /var/lib/tbench/.reference.json - verification data
"""

import json
import os
import struct
import hashlib
import random

FRAME_SIZE = 64
BLOCK_SIZE = 16
NUM_FRAMES = 300
XOR_KEY_SIZE = 32

MULTIPLIERS = [1, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]
OFFSETS = [0, 100, 200, 50, 150, 75, 125, 175, 225, 25, 60, 90, 110, 130, 160, 190]

random.seed(0x54454C33)


def generate_permutation(size):
    perm = list(range(size))
    random.shuffle(perm)
    return perm


def generate_xor_key(size):
    return bytes(random.randint(0, 255) for _ in range(size))


def apply_permutation(data, perm):
    """out[i] = data[perm[i]]"""
    out = bytearray(len(data))
    for i, p in enumerate(perm):
        out[i] = data[p]
    return bytes(out)


def build_header(seq):
    """Build 16-byte header from sequence number."""
    return bytes((seq * m + o) % 256 for m, o in zip(MULTIPLIERS, OFFSETS))


def encrypt_frame(plaintext, perm, xor_key):
    assert len(plaintext) == FRAME_SIZE
    permuted = bytearray()
    for blk in range(0, FRAME_SIZE, BLOCK_SIZE):
        block = plaintext[blk:blk + BLOCK_SIZE]
        permuted.extend(apply_permutation(block, perm))
    encrypted = bytearray(FRAME_SIZE)
    for i in range(FRAME_SIZE):
        encrypted[i] = permuted[i] ^ xor_key[i % XOR_KEY_SIZE]
    return bytes(encrypted)


def build_plaintext_frame(frame_id):
    header = build_header(frame_id)
    payload = bytes(random.randint(0, 255) for _ in range(32))
    padding = b'\x00' * 16
    frame = header + payload + padding
    assert len(frame) == FRAME_SIZE
    return frame


def main():
    perm = generate_permutation(BLOCK_SIZE)
    xor_key = generate_xor_key(XOR_KEY_SIZE)

    plaintext_frames = []
    encrypted_frames = []

    for i in range(NUM_FRAMES):
        pt = build_plaintext_frame(i)
        plaintext_frames.append(pt)
        ct = encrypt_frame(pt, perm, xor_key)
        encrypted_frames.append(ct)

    os.makedirs('/app', exist_ok=True)
    with open('/app/telemetry.bin', 'wb') as f:
        for ct in encrypted_frames:
            f.write(ct)

    frame_hashes = [hashlib.sha256(pt).hexdigest() for pt in plaintext_frames]
    all_pt = b''.join(plaintext_frames)
    full_hash = hashlib.sha256(all_pt).hexdigest()

    reference = {
        'num_frames': NUM_FRAMES,
        'frame_size': FRAME_SIZE,
        'block_size': BLOCK_SIZE,
        'xor_key_size': XOR_KEY_SIZE,
        'full_plaintext_hash': full_hash,
        'frame_hashes': frame_hashes,
        'permutation': perm,
        'xor_key': list(xor_key),
    }

    os.makedirs('/var/lib/tbench', exist_ok=True)
    with open('/var/lib/tbench/.reference.json', 'w') as f:
        json.dump(reference, f)

    print(f"Generated {NUM_FRAMES} frames -> /app/telemetry.bin")
    print(f"Permutation: {perm}")
    print(f"XOR key: {list(xor_key)}")
    print(f"Full SHA256: {full_hash}")


if __name__ == '__main__':
    main()
