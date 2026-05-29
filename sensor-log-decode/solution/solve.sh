#!/bin/bash
cat > /app/extract.py << 'PYTHON'
import struct
import json
import os
import hashlib
from collections import defaultdict

SENSORS = ["temp-A1", "temp-A2", "temp-B1", "pressure-B3", "pressure-C1",
           "humidity-C2", "humidity-D1", "flow-E1", "flow-E2", "vibration-F1"]

def reconstruct_frames(num=50):
    import random
    random.seed(77777)
    frames = []
    for i in range(num):
        sensor = SENSORS[i % len(SENSORS)]
        day = (i // 24) + 1
        hour = i % 24
        minute = (i * 7) % 60
        ts = f"2024-03-{day:02d}T{hour:02d}:{minute:02d}:00Z"
        value = round(random.uniform(5.0, 950.0), 4)
        frame = bytearray(64)
        struct.pack_into('<I', frame, 0, i)
        name = sensor.encode()[:16]
        frame[4:4+len(name)] = name
        ts_bytes = ts.encode()[:24]
        frame[20:20+len(ts_bytes)] = ts_bytes
        struct.pack_into('<d', frame, 44, value)
        frames.append(frame)
    return frames

def main():
    with open("/app/data/sensorlog.dat", "rb") as f:
        data = bytearray(f.read())

    expected_frames = reconstruct_frames(50)
    expected = bytearray()
    for ef in expected_frames:
        expected.extend(ef)

    # Try block sizes from 8 to 32
    for block_size in range(8, 33):
        # Try XOR key lengths from 16 to 32
        for key_len in [24, 16, 32, 20, 12]:
            # Use pairs of frames to cancel XOR and find permutation
            inv_perm_possible = [set(range(block_size)) for _ in range(block_size)]

            for fa, fb in [(0,1),(0,2),(1,2),(0,3),(1,3),(2,4),(0,5),(3,5),(1,6),(0,7)]:
                for block_num in range(64 // block_size):
                    off_a = fa * 64 + block_num * block_size
                    off_b = fb * 64 + block_num * block_size
                    if off_a + block_size > len(data) or off_b + block_size > len(data):
                        continue
                    if off_a + block_size > len(expected) or off_b + block_size > len(expected):
                        continue
                    if off_a % key_len != off_b % key_len:
                        continue

                    s_a = data[off_a:off_a+block_size]
                    s_b = data[off_b:off_b+block_size]

                    # Before permutation, XOR was applied. We need XORed expected.
                    # But we don't know XOR key yet.
                    # After XOR then permutation: final[PERM[i]] = xored[i]
                    # XOR of two final blocks at same key offset:
                    # final_a[p] XOR final_b[p] = xored_a[inv_perm[p]] XOR xored_b[inv_perm[p]]
                    # = (orig_a[inv_perm[p]] ^ key) XOR (orig_b[inv_perm[p]] ^ key)
                    # = orig_a[inv_perm[p]] XOR orig_b[inv_perm[p]]

                    e_a = expected[off_a:off_a+block_size]
                    e_b = expected[off_b:off_b+block_size]

                    xs = bytes(a ^ b for a, b in zip(s_a, s_b))
                    xe = bytes(a ^ b for a, b in zip(e_a, e_b))

                    for p in range(block_size):
                        valid = {q for q in range(block_size) if xs[p] == xe[q]}
                        inv_perm_possible[p] = inv_perm_possible[p].intersection(valid)

            # Resolve
            inv_perm = [None] * block_size
            resolved = set()
            changed = True
            while changed:
                changed = False
                for p in range(block_size):
                    remaining = inv_perm_possible[p] - resolved
                    inv_perm_possible[p] = remaining
                    if len(remaining) == 1:
                        val = next(iter(remaining))
                        if inv_perm[p] is None:
                            inv_perm[p] = val
                            resolved.add(val)
                            changed = True

            if None in inv_perm:
                continue

            # Recover XOR key
            key = bytearray(key_len)
            key_found = [False] * key_len
            for frame_idx in range(10):
                for block_num in range(64 // block_size):
                    off = frame_idx * 64 + block_num * block_size
                    for p in range(block_size):
                        key_pos = (off + inv_perm[p]) % key_len
                        if not key_found[key_pos]:
                            orig_byte = expected[frame_idx * 64 + block_num * block_size + inv_perm[p]]
                            # final[p] = xored[inv_perm[p]] after permutation
                            # But permutation maps: final[PERM[i]] = xored[i]
                            # So final[p] came from xored[inv_perm[p]]
                            # xored[inv_perm[p]] = orig[inv_perm[p]] ^ key[(off + inv_perm[p]) % key_len]
                            # We need to un-permute first to get xored
                            # un_permuted[inv_perm[p]] = data[off + p]
                            # So: data[off + p] = orig[inv_perm[p]] ^ key[(off + inv_perm[p]) % key_len]
                            key[key_pos] = data[off + p] ^ orig_byte
                            key_found[key_pos] = True

            if not all(key_found):
                continue

            # Decrypt: reverse permutation then reverse XOR
            unpermuted = bytearray(len(data))
            for block_start in range(0, len(data), block_size):
                block = data[block_start:block_start+block_size]
                if len(block) < block_size:
                    unpermuted[block_start:block_start+len(block)] = block
                    continue
                for p in range(block_size):
                    unpermuted[block_start + inv_perm[p]] = block[p]

            decrypted = bytearray(len(unpermuted))
            for i in range(len(unpermuted)):
                decrypted[i] = unpermuted[i] ^ key[i % key_len]

            # Verify
            test_seq = struct.unpack_from('<I', decrypted, 0)[0]
            if test_seq != 0:
                continue
            test_seq1 = struct.unpack_from('<I', decrypted, 64)[0]
            if test_seq1 != 1:
                continue

            # Parse all records
            records = []
            for idx in range(300):
                off = idx * 64
                seq = struct.unpack_from('<I', decrypted, off)[0]
                sensor = decrypted[off+4:off+20].split(b'\x00')[0].decode()
                timestamp = decrypted[off+20:off+44].split(b'\x00')[0].decode()
                value = struct.unpack_from('<d', decrypted, off+44)[0]
                records.append({"seq": seq, "sensor": sensor, "timestamp": timestamp, "value": round(value, 4)})

            records.sort(key=lambda r: r["seq"])
            os.makedirs("/app/output", exist_ok=True)
            with open("/app/output/readings.json", "w") as f:
                json.dump(records, f, indent=2)
            print(f"Decoded {len(records)} records")
            return

    print("ERROR: Could not decode")

if __name__ == "__main__":
    main()
PYTHON

python /app/extract.py
