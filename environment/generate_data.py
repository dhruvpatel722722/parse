#!/usr/bin/env python3
"""Generate scrambled sensor readings."""
import json, os, struct, hashlib, random, zlib

READING_SIZE = 96
BLOCK_SIZE = 12
NUM_READINGS = 200
KEY_SIZE = 12
MULT = [23, 1, 41, 7, 31, 11, 3, 37, 29, 13, 19, 17]
OFF = [175, 0, 60, 100, 225, 150, 50, 10, 200, 25, 75, 125]

random.seed(0x48415244)


def gen_perm(n):
    p = list(range(n))
    random.shuffle(p)
    return p


def gen_key(n):
    return bytes(random.randint(0, 255) for _ in range(n))


def apply_perm(data, perm):
    out = bytearray(len(data))
    for i, p in enumerate(perm):
        out[i] = data[p]
    return bytes(out)


def scramble(plaintext, perm, key):
    assert len(plaintext) == READING_SIZE
    permuted = bytearray()
    for b in range(0, READING_SIZE, BLOCK_SIZE):
        permuted.extend(apply_perm(plaintext[b:b+BLOCK_SIZE], perm))
    out = bytearray(READING_SIZE)
    for i in range(READING_SIZE):
        out[i] = permuted[i] ^ key[i % KEY_SIZE]
    return bytes(out)


def build_header(idx):
    return bytes((idx * m + o) % 256 for m, o in zip(MULT, OFF))


def build_reading(idx):
    header = build_header(idx)
    payload = bytes(random.randint(0, 255) for _ in range(72))
    padding = b'\x00' * 12
    return header + payload + padding


def main():
    perm = gen_perm(BLOCK_SIZE)
    key = gen_key(KEY_SIZE)
    pts, cts = [], []
    for i in range(NUM_READINGS):
        pt = build_reading(i)
        pts.append(pt)
        cts.append(scramble(pt, perm, key))

    os.makedirs('/app', exist_ok=True)
    with open('/app/readings.bin', 'wb') as f:
        for c in cts:
            f.write(c)

    hashes = [hashlib.sha256(p).hexdigest() for p in pts]
    full = hashlib.sha256(b''.join(pts)).hexdigest()
    ref = {
        'num_readings': NUM_READINGS,
        'reading_size': READING_SIZE,
        'block_size': BLOCK_SIZE,
        'key_size': KEY_SIZE,
        'full_hash': full,
        'reading_hashes': hashes,
        'permutation': perm,
        'xor_key': list(key),
        'multipliers': MULT,
        'offsets': OFF,
    }
    os.makedirs('/var/lib/tbench', exist_ok=True)
    with open('/var/lib/tbench/.reference.json', 'w') as f:
        json.dump(ref, f)
    print(f"OK: perm={perm}, key_len={KEY_SIZE}, SHA256={full}")


if __name__ == '__main__':
    main()
