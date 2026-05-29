#!/bin/bash
cat > /app/recover.py << 'PYTHON'
import struct
import json
import os
import hashlib
from collections import defaultdict

WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
         "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi",
         "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
         "config", "server", "client", "cache", "queue", "index", "route", "token"]

def reconstruct_expected_frames(num_frames=50):
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

def recover_xor_key(scrambled, expected_permuted, key_len=32):
    """Recover XOR key by comparing scrambled bytes with expected permuted bytes."""
    key = bytearray(key_len)
    for i in range(key_len):
        key[i] = scrambled[i] ^ expected_permuted[i]
    return key

def main():
    with open("/app/data/records.dat", "rb") as f:
        data = bytearray(f.read())
    
    expected_frames = reconstruct_expected_frames(50)
    
    # Step 1: We know the permutation was applied first, then XOR.
    # To find XOR key, we need to know what the permuted data looks like.
    # But we don't know the permutation yet either.
    # 
    # Strategy: Try all possible XOR key lengths and permutations together.
    # Actually: we can use the known structure. Frame 0 has id=0 (bytes 00 00 00 00).
    # After permutation, those zeros are scattered. After XOR, those positions
    # reveal the XOR key directly (since 0 XOR key[i] = key[i]).
    #
    # Frame 0, bytes 0-3 are all 0x00 in the original.
    # After permutation, position PERM[0], PERM[1], PERM[2], PERM[3] in the permuted
    # block get the values 0x00. After XOR, those positions show the raw key bytes.
    #
    # But we don't know PERM yet. However, we know bytes 0-3 of frame 0 are 0,
    # AND many null-padding bytes in the frame are also 0.
    # 
    # Better: use frame 0's known content to determine XOR key first.
    # If we assume XOR key repeats every K bytes, then for any position where
    # the PERMUTED byte is known, we can extract key[pos % K].
    #
    # Let's try: assume the XOR key repeats with period dividing 32 (common).
    # For frame 1 (id=1), byte 0 of original is 0x01, bytes 1-3 are 0x00.
    # After permutation within the first 16-byte block, these land somewhere.
    # After XOR, we see the scrambled values.
    #
    # Alternative approach: try key lengths 16, 32. For each, use the fact that
    # many frame bytes are 0x00 (null padding) which means scrambled = key XOR permuted_zero = key.
    
    # Frames are 128 bytes. Positions 36+len(value)..127 are null in most frames.
    # After permutation, nulls scatter. After XOR with key, nulls become key bytes.
    # This means in the scrambled data, positions that correspond to null bytes 
    # after permutation will directly show the XOR key.
    
    # Try key_len = 32: look at tail of frame 0 (lots of nulls in value area)
    # Frame 0 value: about 60-70 chars, so bytes ~100-127 are null.
    # These are in blocks 6 and 7 of the frame (block 6: bytes 96-111, block 7: 112-127)
    
    # Actually let's just try brute force with known plaintext.
    # We know frame 0 entirely. After permutation it becomes some known bytes.
    # We try all 16! permutations? No, too many.
    
    # Smart approach: try XOR key = 32, guess that permutation block = 16.
    # Use multiple frames where we know BOTH the original AND that
    # some bytes are unique to pin down the permutation.
    
    # Simplest: frame 0 has many zeros. After perm, zeros scatter. After XOR, 
    # positions that had zeros show the raw key. Positions that had non-zero show
    # value XOR key. If we XOR the scrambled data with itself shifted by 128 bytes
    # (frame period), the key cancels and we see perm(frame0) XOR perm(frame1).
    
    # CLEANEST APPROACH: Reconstruct expected frames, apply candidate permutations,
    # XOR with scrambled data, check if XOR key is consistent.
    
    # Since we know expected frame content, let's directly solve:
    # scrambled[i] = permuted[i] XOR key[i % key_len]
    # permuted comes from applying perm to original frames.
    
    # If we know the original frame 0 content fully, and we try all possible
    # permutations of the first 16-byte block, for each candidate perm we get
    # candidate permuted bytes, then candidate key bytes = scrambled XOR permuted.
    # We check if this key is consistent across the whole file.
    
    # For a 16-element permutation, 16! is too large. But we can use constraints.
    # Use frame 0 block 0: original is [0,0,0,0, 97,108,112,104, 97,46,100,101, 108,116,97,46]
    # Many bytes are known. We need to find perm such that for each position p:
    #   key[(block_offset + PERM[i]) % key_len] = scrambled[block_offset + PERM[i]] XOR original[block_offset + i]
    # This must be consistent across all blocks.
    
    # Let me use a constraint-based approach across multiple blocks:
    expected = bytearray()
    for ef in expected_frames:
        expected.extend(ef)
    
    # Try all possible XOR key lengths that divide 128
    # Most likely: 16 or 32
    for key_len in [32, 16]:
        # For each pair of blocks at same offset modulo key_len,
        # the XOR key contribution is the same.
        # So: scrambled[i] XOR scrambled[j] = permuted[i] XOR permuted[j]
        #     when i % key_len == j % key_len
        # This eliminates the key and lets us work with permuted differences.
        
        # Assume perm block size = 16. Try to find perm using constraint propagation.
        possible = [set(range(16)) for _ in range(16)]
        
        for frame_idx in range(30):
            for block_num in range(8):
                off = frame_idx * 128 + block_num * 16
                s_block = data[off:off+16]
                e_block = expected[off:off+16]
                
                for i in range(16):
                    # If perm maps position i in original to position p in permuted:
                    # permuted[p] = original[i]
                    # scrambled[p] = permuted[p] XOR key[(off+p) % key_len]
                    # So: key[(off+p) % key_len] = scrambled[p] XOR original[i]
                    # This key value must be consistent for the same (off+p) % key_len across all blocks.
                    pass
        
        # Better: directly solve using the known-plaintext attack.
        # Pick two blocks at offsets that share the same key positions.
        # E.g., block at offset 0 and block at offset 32 (if key_len=32, same key slice).
        # Or block at offset 0 and offset 128 (frame 1, same key positions if key_len divides 128).
        
        # Since key_len=32 divides 128, blocks at offset 0 in frame 0 and frame 1 
        # use the same key[0:16].
        # scrambled_f0_b0[p] = perm(original_f0_b0)[p] XOR key[p % 32]
        # scrambled_f1_b0[p] = perm(original_f1_b0)[p] XOR key[p % 32]
        # XOR them: scrambled_f0_b0[p] XOR scrambled_f1_b0[p] = perm(orig_f0_b0)[p] XOR perm(orig_f1_b0)[p]
        # = orig_f0_b0[inv_perm[p]] XOR orig_f1_b0[inv_perm[p]]
        # This gives us: for each position p, the XOR of the two original values at inv_perm[p]
        
        # We know orig_f0_b0 and orig_f1_b0 completely.
        # So for each candidate mapping inv_perm[p] = q:
        #   scrambled_f0[p] XOR scrambled_f1[p] must equal orig_f0[q] XOR orig_f1[q]
        
        # This is a strong constraint!
        s_f0_b0 = data[0:16]
        s_f1_b0 = data[128:144]
        e_f0_b0 = expected[0:16]
        e_f1_b0 = expected[128:144]
        
        xor_scrambled = bytes(a ^ b for a, b in zip(s_f0_b0, s_f1_b0))
        xor_expected = bytes(a ^ b for a, b in zip(e_f0_b0, e_f1_b0))
        
        # For each p: xor_scrambled[p] == xor_expected[inv_perm[p]]
        # Find inv_perm
        inv_perm_possible = [set(range(16)) for _ in range(16)]
        
        # Use multiple frame pairs for stronger constraints
        for fa, fb in [(0,1), (0,2), (1,2), (0,3), (2,3), (0,4), (1,4), (3,5), (0,6), (1,7)]:
            for block_num in range(8):
                off_a = fa * 128 + block_num * 16
                off_b = fb * 128 + block_num * 16
                if off_a + 16 > len(data) or off_b + 16 > len(data):
                    continue
                if off_a + 16 > len(expected) or off_b + 16 > len(expected):
                    continue
                    
                s_a = data[off_a:off_a+16]
                s_b = data[off_b:off_b+16]
                e_a = expected[off_a:off_a+16]
                e_b = expected[off_b:off_b+16]
                
                # Only works if key positions align (same offset mod key_len)
                if off_a % key_len != off_b % key_len:
                    # Key bytes differ, can't cancel
                    continue
                
                xs = bytes(a ^ b for a, b in zip(s_a, s_b))
                xe = bytes(a ^ b for a, b in zip(e_a, e_b))
                
                for p in range(16):
                    valid = {q for q in range(16) if xs[p] == xe[q]}
                    inv_perm_possible[p] = inv_perm_possible[p].intersection(valid)
        
        # Resolve by elimination
        inv_perm = [None] * 16
        resolved = set()
        changed = True
        while changed:
            changed = False
            for p in range(16):
                remaining = inv_perm_possible[p] - resolved
                inv_perm_possible[p] = remaining
                if len(remaining) == 1:
                    val = next(iter(remaining))
                    if inv_perm[p] is None:
                        inv_perm[p] = val
                        resolved.add(val)
                        changed = True
        
        if None in inv_perm:
            continue  # Try next key_len
        
        # Now recover the XOR key using inv_perm and known plaintext
        # permuted[p] = original[inv_perm[p]]
        # scrambled[off + p] = permuted[p] XOR key[(off + p) % key_len]
        # key[(off + p) % key_len] = scrambled[off + p] XOR original_frame[inv_perm[p]]
        
        key = bytearray(key_len)
        key_found = [False] * key_len
        
        for frame_idx in range(10):
            for block_num in range(8):
                off = frame_idx * 128 + block_num * 16
                for p in range(16):
                    key_pos = (off + p) % key_len
                    if not key_found[key_pos]:
                        orig_val = expected[off - frame_idx*128 + frame_idx*128 + block_num*16 + inv_perm[p]]
                        # Simpler: expected already has full frames concatenated
                        orig_byte = expected[frame_idx * 128 + block_num * 16 + inv_perm[p]]
                        key[key_pos] = data[off + p] ^ orig_byte
                        key_found[key_pos] = True
        
        if not all(key_found):
            continue
        
        # Decrypt full file: reverse XOR then reverse permutation
        decrypted = bytearray(len(data))
        for i in range(len(data)):
            decrypted[i] = data[i] ^ key[i % key_len]
        
        # Reverse permutation (decrypted has permuted data)
        # permuted[PERM[i]] = original[i], so original[i] = permuted[PERM[i]]
        # But we found inv_perm where: permuted[p] = original[inv_perm[p]]
        # So original[inv_perm[p]] = permuted[p]
        # Or: original[q] = permuted[perm[q]] where perm is the forward permutation
        # inv_perm[p] = q means permuted position p came from original position q
        # So to get original: original[q] = permuted[p] where inv_perm[p] = q
        # Equivalently: for each block, original[inv_perm[p]] = permuted[p] for all p
        
        restored = bytearray(len(decrypted))
        for block_start in range(0, len(decrypted), 16):
            block = decrypted[block_start:block_start+16]
            for p in range(16):
                restored[block_start + inv_perm[p]] = block[p]
        
        # Verify first frame
        test_id = struct.unpack_from('<I', restored, 0)[0]
        if test_id != 0:
            continue
        
        # Parse all frames
        records = []
        for frame_idx in range(200):
            off = frame_idx * 128
            rec_id = struct.unpack_from('<I', restored, off)[0]
            key_bytes = restored[off+4:off+36].split(b'\x00')[0].decode('utf-8')
            val_bytes = restored[off+36:off+128].split(b'\x00')[0].decode('utf-8')
            records.append({"id": rec_id, "key": key_bytes, "value": val_bytes})
        
        records.sort(key=lambda r: r["id"])
        
        os.makedirs("/app/output", exist_ok=True)
        with open("/app/output/recovered.json", "w") as f:
            json.dump(records, f, indent=2)
        
        print(f"Recovered {len(records)} records")
        return
    
    print("ERROR: Could not determine transformations")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
