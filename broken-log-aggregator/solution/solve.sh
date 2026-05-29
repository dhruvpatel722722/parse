#!/bin/bash
# Recover scrambled database by determining the block permutation

cat > /app/recover.py << 'PYTHON'
import struct
import json
import os
import hashlib
from collections import Counter

def reconstruct_expected_frames(num_frames=50):
    """Reconstruct what the original frames should look like."""
    WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
             "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi",
             "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
             "config", "server", "client", "cache", "queue", "index", "route", "token"]
    
    frames = []
    for i in range(num_frames):
        prefix = WORDS[i % len(WORDS)]
        suffix = WORDS[(i * 7 + 3) % len(WORDS)]
        key_str = f"{prefix}.{suffix}.{i:03d}"
        val_words = [WORDS[(i * 11 + j * 5) % len(WORDS)] for j in range(4)]
        value = f"data={'.'.join(val_words)} seq={i:04d} hash={hashlib.md5(str(i).encode()).hexdigest()[:8]}"
        
        frame = bytearray(128)
        struct.pack_into('<I', frame, 0, i)
        k = key_str.encode()[:32]
        frame[4:4+len(k)] = k
        v = value.encode()[:92]
        frame[36:36+len(v)] = v
        frames.append(frame)
    
    return frames

def deduce_permutation(scrambled_data):
    """Deduce the 16-byte block permutation using known frame content."""
    expected_frames = reconstruct_expected_frames(50)
    
    # The relationship is: scrambled[PERM[i]] = original[i]
    # To recover: original[i] = scrambled[PERM[i]]
    # So we need to find PERM such that for each block:
    #   scrambled_block[PERM[i]] == expected_block[i] for all i
    
    # Use constraint propagation across multiple blocks
    possible = [set(range(16)) for _ in range(16)]
    
    for frame_idx in range(50):
        expected_frame = expected_frames[frame_idx]
        # Process each 16-byte block within this frame
        for block_num in range(8):  # 128/16 = 8 blocks per frame
            block_offset = frame_idx * 128 + block_num * 16
            scrambled_block = scrambled_data[block_offset:block_offset+16]
            expected_block = expected_frame[block_num*16:(block_num+1)*16]
            
            # For each position i in the original:
            # scrambled_block[PERM[i]] must equal expected_block[i]
            for i in range(16):
                target_val = expected_block[i]
                valid_positions = frozenset(
                    p for p in range(16) if scrambled_block[p] == target_val
                )
                possible[i] = possible[i].intersection(valid_positions)
    
    # Resolve by elimination
    perm = [None] * 16
    resolved = set()
    
    changed = True
    while changed:
        changed = False
        for i in range(16):
            remaining = possible[i] - resolved
            if len(remaining) == 1:
                val = next(iter(remaining))
                if perm[i] is None:
                    perm[i] = val
                    resolved.add(val)
                    changed = True
            possible[i] = remaining
    
    # Verify completeness
    if None in perm:
        raise ValueError(f"Could not fully resolve permutation: {perm}")
    
    return perm

def main():
    with open("/app/data/records.dat", "rb") as f:
        data = bytearray(f.read())
    
    # Deduce the permutation
    perm = deduce_permutation(data)
    
    # Unscramble entire file
    unscrambled = bytearray(len(data))
    for block_start in range(0, len(data), 16):
        block = data[block_start:block_start+16]
        for i in range(16):
            unscrambled[block_start + i] = block[perm[i]]
    
    # Parse frames
    records = []
    for frame_idx in range(200):
        offset = frame_idx * 128
        rec_id = struct.unpack_from('<I', unscrambled, offset)[0]
        key_bytes = unscrambled[offset+4:offset+36]
        key = key_bytes.split(b'\x00')[0].decode('utf-8')
        val_bytes = unscrambled[offset+36:offset+128]
        value = val_bytes.split(b'\x00')[0].decode('utf-8')
        records.append({"id": rec_id, "key": key, "value": value})
    
    records.sort(key=lambda r: r["id"])
    
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/recovered.json", "w") as f:
        json.dump(records, f, indent=2)
    
    print(f"Recovered {len(records)} records")
    print(f"First: id={records[0]['id']} key={records[0]['key']}")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
