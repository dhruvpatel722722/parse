#!/usr/bin/env python3
"""Generate the corrupted binary database for the custom-compression-algorithm task."""
import hashlib
import json
import os
import struct
import random

SEED = 0xCAFE_BABE
NUM_RECORDS = 200
FRAME_SIZE = 128
ID_SIZE = 4
KEY_SIZE = 32
VALUE_SIZE = 92

# Vocabularies for key generation
GREEK = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi",
    "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega"
]

TECH = [
    "kernel", "socket", "buffer", "cache", "thread", "mutex", "queue", "stack",
    "heap", "token", "cipher", "codec", "proxy", "router", "bridge", "driver",
    "daemon", "signal", "packet", "stream", "vector", "matrix", "tensor", "shader"
]

VOCAB = GREEK + TECH  # 48 words total


def generate_records(rng):
    """Generate 200 original plaintext records."""
    records = []
    for i in range(NUM_RECORDS):
        # Key: word.word.NNN
        w1 = rng.choice(VOCAB)
        w2 = rng.choice(VOCAB)
        num = rng.randint(100, 999)
        key = f"{w1}.{w2}.{num}"

        # Value: data=<16 hex chars>, seq=<number>, hash=<8 hex chars>
        # hash is first 8 chars of sha256(data_hex + str(seq_num)) for verifiability
        data_hex = ''.join(rng.choices('0123456789abcdef', k=16))
        seq_num = rng.randint(1000, 99999)
        import hashlib
        hash_input = (data_hex + str(seq_num)).encode()
        hash_hex = hashlib.sha256(hash_input).hexdigest()[:8]
        value = f"data={data_hex}, seq={seq_num}, hash={hash_hex}"

        records.append({"id": i, "key": key, "value": value})
    return records


def record_to_frame(record):
    """Convert a record dict to a 128-byte plaintext frame."""
    frame = bytearray(FRAME_SIZE)
    # ID: 4 bytes little-endian
    struct.pack_into('<I', frame, 0, record["id"])
    # Key: 32 bytes, null-padded
    key_bytes = record["key"].encode('ascii')
    frame[ID_SIZE:ID_SIZE + len(key_bytes)] = key_bytes
    # Value: 92 bytes, null-padded
    val_bytes = record["value"].encode('ascii')
    frame[ID_SIZE + KEY_SIZE:ID_SIZE + KEY_SIZE + len(val_bytes)] = val_bytes
    return bytes(frame)


def generate_permutation(rng):
    """Generate a fixed 16-element permutation for block shuffling."""
    perm = list(range(16))
    rng.shuffle(perm)
    return perm


def generate_xor_key(rng):
    """Generate a 128-byte XOR key for positional encryption."""
    return bytes(rng.randint(0, 255) for _ in range(FRAME_SIZE))


def apply_block_shuffle(frame, perm):
    """Shuffle 8-byte blocks within a 128-byte frame using the permutation."""
    block_size = FRAME_SIZE // len(perm)  # 128/16 = 8 bytes per block
    blocks = [frame[i * block_size:(i + 1) * block_size] for i in range(len(perm))]
    shuffled = bytearray(FRAME_SIZE)
    for dst_idx, src_idx in enumerate(perm):
        shuffled[dst_idx * block_size:(dst_idx + 1) * block_size] = blocks[src_idx]
    return bytes(shuffled)


def apply_xor(frame, xor_key):
    """XOR each byte of the frame with the positional key."""
    return bytes(a ^ b for a, b in zip(frame, xor_key))


def main():
    rng = random.Random(SEED)

    # Generate original records
    records = generate_records(rng)

    # Generate transformation parameters
    perm = generate_permutation(rng)
    xor_key = generate_xor_key(rng)

    # Build corrupted binary
    corrupted_data = bytearray()
    for record in records:
        frame = record_to_frame(record)
        # Step 1: Block shuffle
        shuffled = apply_block_shuffle(frame, perm)
        # Step 2: XOR
        encrypted = apply_xor(shuffled, xor_key)
        corrupted_data.extend(encrypted)

    # Write corrupted data
    os.makedirs("/app/data", exist_ok=True)
    with open("/app/data/records.dat", "wb") as f:
        f.write(corrupted_data)

    # Write reference JSON for test verification
    os.makedirs("/var/lib/tbench", exist_ok=True)
    reference = sorted(records, key=lambda r: r["id"])
    with open("/var/lib/tbench/.reference.json", "w") as f:
        json.dump(reference, f, indent=2)

    # Set restrictive permissions on reference
    os.chmod("/var/lib/tbench/.reference.json", 0o600)
    os.chmod("/var/lib/tbench", 0o700)

    print(f"Generated {len(corrupted_data)} bytes of corrupted data ({NUM_RECORDS} records)")
    print(f"Permutation (16 blocks of 8 bytes): {perm}")
    print(f"XOR key length: {len(xor_key)} bytes")
    print(f"Reference saved to /var/lib/tbench/.reference.json")


if __name__ == "__main__":
    main()
