#!/bin/bash
cat > /app/recover.py << 'PYTHON'
import struct, json, os
from itertools import permutations

def main():
    with open("/app/data/records.dat", "rb") as f:
        data = bytearray(f.read())

    NUM = 200       # number of records
    FRAME = 128     # bytes per frame
    BLK = 16        # block size for permutation
    KLEN = 32       # XOR key length (repeating)

    # =========================================================================
    # Known-plaintext attack using frame structure:
    #
    # Frame layout (128 bytes):
    #   [0:4]    = 4-byte LE sequential id (0..199)
    #   [4:36]   = 32-byte null-padded key (format: word.word.NNN, max ~17 chars)
    #   [36:128] = 92-byte null-padded value (format: data=... seq=NNNN hash=..., max ~57 chars)
    #
    # Since values are at most ~60 chars, frame bytes 96-127 are ALWAYS zero.
    # These correspond to blocks 6 (bytes 96-111) and 7 (bytes 112-127).
    #
    # Encoding order: permute 16-byte blocks FIRST, then XOR with 32-byte key.
    # Decoding order: undo XOR first, then undo permutation.
    #
    # PHASE 1: Recover XOR key from all-zero blocks.
    #   Permuting all-zeros yields all-zeros.
    #   encrypted[i] = 0 XOR key[i%32] = key[i%32]
    #   Block 6 at offset 96 (96%32=0): reveals key[0:16]
    #   Block 7 at offset 112 (112%32=16): reveals key[16:32]
    #
    # PHASE 2: Recover permutation using structural constraints.
    #   After XOR removal, data is permuted. Use known byte patterns:
    #   - Block 0: bytes 0-3 = LE id, bytes 4-15 = key prefix
    #   - Block 2 (frame bytes 32-47): bytes 32-35 = key padding (zeros),
    #     bytes 36-47 = value[0:12] which always starts with "data=" (constant chars)
    #   These give us enough constraints to identify most PERM entries, with
    #   a small brute-force (max 60480 trials) for the remainder.
    # =========================================================================

    # === PHASE 1: Recover XOR key from zero-padded blocks ===
    key = bytearray(KLEN)
    for p in range(BLK):
        key[p] = data[96 + p]          # block 6: key positions 0-15
        key[16 + p] = data[112 + p]    # block 7: key positions 16-31

    # === PHASE 2: Remove XOR from all data ===
    dec = bytearray(len(data))
    for i in range(len(data)):
        dec[i] = data[i] ^ key[i % KLEN]
    # Now: dec[frame_off + blk*16 + PERM[i]] = original[frame_off + blk*16 + i]

    # === PHASE 3: Identify known permutation entries ===

    # PERM[0]: position in block 0 that holds the frame id (0..199)
    perm0 = None
    for pos in range(BLK):
        if all(dec[f * FRAME + pos] == f for f in range(NUM)):
            perm0 = pos
            break

    # Positions always-zero in block 0: candidates for PERM[1,2,3]
    # (since ids < 256, the upper 3 bytes of the 4-byte LE id are always 0)
    always_zero_b0 = [pos for pos in range(BLK)
                      if pos != perm0 and all(dec[f*FRAME+pos] == 0 for f in range(NUM))]

    # Block 2 analysis (frame bytes 32-47):
    # Original positions 0-3 in block 2 = frame bytes 32-35 = key[28:32] = always 0
    # Original position 4 = frame byte 36 = value[0] = 'd' (100)
    # Original position 5 = value[1] = 'a' (97)
    # Original position 6 = value[2] = 't' (116)
    # Original position 7 = value[3] = 'a' (97)
    # Original position 8 = value[4] = '=' (61)
    # Original positions 9-15 = value[5:12] (variable word characters)

    # Find positions with constant values in block 2
    const_zero_b2 = [pos for pos in range(BLK)
                     if all(dec[f*FRAME+32+pos] == 0 for f in range(NUM))]

    const_val_b2 = {}
    for pos in range(BLK):
        vals = set(dec[f * FRAME + 32 + pos] for f in range(NUM))
        if len(vals) == 1:
            const_val_b2[pos] = vals.pop()

    # Identify specific PERM entries from block 2 constants
    pos_d = [p for p, v in const_val_b2.items() if v == 100]   # 'd' -> PERM[4]
    pos_t = [p for p, v in const_val_b2.items() if v == 116]   # 't' -> PERM[6]
    pos_eq = [p for p, v in const_val_b2.items() if v == 61]   # '=' -> PERM[8]
    pos_a = [p for p, v in const_val_b2.items() if v == 97]    # 'a' -> PERM[5] and PERM[7]

    # PERM[1,2,3]: intersection of always_zero_b0 and const_zero_b2
    # (positions that are zero in both block 0 and block 2 must be id-high-bytes)
    perm123_positions = [p for p in always_zero_b0 if p in const_zero_b2]

    # Build the fixed assignments we're confident about
    fixed = {}
    fixed[0] = perm0
    if pos_d: fixed[4] = pos_d[0]
    if pos_t: fixed[6] = pos_t[0]
    if pos_eq: fixed[8] = pos_eq[0]

    # Positions assigned to groups for brute force
    group_123_positions = perm123_positions[:3]  # PERM[1,2,3] - order unknown (3! = 6)
    group_57_positions = pos_a[:2]               # PERM[5,7] - order unknown (2! = 2)

    # Remaining positions for PERM[9..15]
    all_assigned = set(fixed.values()) | set(group_123_positions) | set(group_57_positions)
    group_rest_positions = sorted([p for p in range(BLK) if p not in all_assigned])

    # === PHASE 4: Brute-force remaining assignments (max 6*2*5040 = 60480 trials) ===
    best_perm = None
    best_score = -1

    for p123 in permutations(group_123_positions):
        for p57 in permutations(group_57_positions):
            for prest in permutations(group_rest_positions):
                trial_perm = [None] * BLK
                trial_perm[0] = fixed[0]
                trial_perm[1], trial_perm[2], trial_perm[3] = p123
                trial_perm[4] = fixed[4]
                trial_perm[5], trial_perm[7] = p57
                trial_perm[6] = fixed[6]
                trial_perm[8] = fixed[8]
                trial_perm[9], trial_perm[10], trial_perm[11] = prest[0], prest[1], prest[2]
                trial_perm[12], trial_perm[13], trial_perm[14], trial_perm[15] = prest[3], prest[4], prest[5], prest[6]

                # Compute inverse permutation
                inv_perm = [0] * BLK
                for i in range(BLK):
                    inv_perm[trial_perm[i]] = i

                # Quick validation: check frame 0 and frame 1 ids
                orig_b0 = [0] * BLK
                for p in range(BLK):
                    orig_b0[inv_perm[p]] = dec[p]
                if orig_b0[0] != 0 or orig_b0[1] != 0 or orig_b0[2] != 0 or orig_b0[3] != 0:
                    continue

                orig_b0_f1 = [0] * BLK
                for p in range(BLK):
                    orig_b0_f1[inv_perm[p]] = dec[FRAME + p]
                if orig_b0_f1[0] != 1 or orig_b0_f1[1] != 0 or orig_b0_f1[2] != 0 or orig_b0_f1[3] != 0:
                    continue

                # Full validation: decode first 5 frames and check value structure
                score = 0
                for f in range(5):
                    orig_frame = bytearray(FRAME)
                    for blk_idx in range(FRAME // BLK):
                        blk_off = f * FRAME + blk_idx * BLK
                        for p in range(BLK):
                            orig_frame[blk_idx * BLK + inv_perm[p]] = dec[blk_off + p]

                    rec_id = struct.unpack_from('<I', orig_frame, 0)[0]
                    if rec_id != f:
                        break

                    value = orig_frame[36:128].split(b'\x00')[0]
                    try:
                        vs = value.decode('ascii')
                        if f"seq={f:04d}" in vs and "data=" in vs and "hash=" in vs:
                            score += 1
                        else:
                            break
                    except:
                        break

                if score > best_score:
                    best_score = score
                    best_perm = trial_perm[:]
                if score >= 5:
                    break
            if best_score >= 5:
                break
        if best_score >= 5:
            break

    # === PHASE 5: Decode all records using recovered permutation ===
    inv_perm = [0] * BLK
    for i in range(BLK):
        inv_perm[best_perm[i]] = i

    records = []
    for f in range(NUM):
        orig_frame = bytearray(FRAME)
        for blk_idx in range(FRAME // BLK):
            blk_off = f * FRAME + blk_idx * BLK
            for p in range(BLK):
                orig_frame[blk_idx * BLK + inv_perm[p]] = dec[blk_off + p]

        rec_id = struct.unpack_from('<I', orig_frame, 0)[0]
        key_str = orig_frame[4:36].split(b'\x00')[0].decode('utf-8', errors='replace')
        val_str = orig_frame[36:128].split(b'\x00')[0].decode('utf-8', errors='replace')
        records.append({"id": rec_id, "key": key_str, "value": val_str})

    records.sort(key=lambda r: r["id"])

    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/recovered.json", "w") as f:
        json.dump(records, f, indent=2)

    print(f"Recovered {len(records)} records successfully")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
