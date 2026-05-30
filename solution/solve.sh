#!/bin/bash
cat > /app/recover.py << 'PYTHON'
import struct, json, os
from itertools import permutations as iterperms

def main():
    with open("/app/data/records.dat", "rb") as f:
        data = bytearray(f.read())

    NUM, FRAME, BLK, KLEN = 200, 128, 16, 32

    # =========================================================================
    # Known-plaintext recovery via XOR-difference permutation analysis.
    # Known per frame (from instruction):
    #   - Bytes 0-3: sequential ID as 4-byte LE (0..199)
    #   - Bytes 116-127: 12 bytes zero padding
    # Structural knowledge (from instruction - values have data=, seq=, hash= fields):
    #   - Values are < 60 chars, so frame bytes 96-127 are always zero
    # Encoding: permute 16-byte blocks, then XOR with 32-byte repeating key.
    # =========================================================================

    # === PHASE 1: Recover XOR key ===
    # Blocks 6-7 (frame bytes 96-127) are all zero before obfuscation.
    # Permuting zeros yields zeros, so after XOR: data[off+p] = KEY[(off+p)%32]
    # Block 6 (offset 96, 96%32=0): gives key[0:16]
    # Block 7 (offset 112, 112%32=16): gives key[16:32]
    key = bytearray(KLEN)
    for p in range(BLK):
        key[p] = data[96 + p]
        key[(16 + p) % KLEN] = data[112 + p]

    # === PHASE 2: Remove XOR key ===
    dec = bytearray(len(data))
    for i in range(len(data)):
        dec[i] = data[i] ^ key[i % KLEN]
    # Now: dec[blk_start + p] = original[blk_start + inv_perm[p]]


    # === PHASE 3: Recover permutation structure ===
    # Block 0: orig[0]=id (varies 0..199), orig[1-3]=0 (ids<256), orig[4-15]=key chars
    # After XOR removal, dec[frame_i + p] = orig_frame_i[inv_perm[p]]

    # Find position where inv_perm[p]=0 (holds the sequential ID for each frame)
    pos0 = None
    for p in range(BLK):
        if all(dec[i * FRAME + p] == i for i in range(NUM)):
            pos0 = p
            break

    # Positions always zero in block 0 across all frames -> inv_perm in {1,2,3}
    always_zero_b0 = [p for p in range(BLK)
                      if p != pos0 and all(dec[i*FRAME+p] == 0 for i in range(NUM))]

    # Block 1 (frame bytes 16-31 = key field bytes 12-27):
    # Keys are max 17 chars, so key_field[17:] = 0, i.e., frame bytes 21+ = 0.
    # Original positions 5-15 in block 1 -> frame bytes 21-31 -> always zero.
    # Positions always zero in block 1 -> inv_perm >= 5
    always_zero_b1 = [p for p in range(BLK)
                      if all(dec[i*FRAME + BLK + p] == 0 for i in range(NUM))]
    # Positions NOT always zero in block 1 -> inv_perm in {0,1,2,3,4}
    not_zero_b1 = [p for p in range(BLK) if p not in always_zero_b1]

    # Block 2 (frame bytes 32-47): orig 0-3 -> frame bytes 32-35 (key padding, always 0)
    # orig 4-15 -> frame bytes 36-47 = value prefix "data=..." (first 5 chars constant)
    const_b2 = {}
    for p in range(BLK):
        val = dec[2*BLK + p]
        if all(dec[i*FRAME + 2*BLK + p] == val for i in range(NUM)):
            const_b2[p] = val


    # === PHASE 4: Assign fixed permutation positions ===
    inv_perm = [None] * BLK
    inv_perm[pos0] = 0

    # Position in not_zero_b1 (inv<=4) that isn't pos0 or always_zero_b0: must be inv=4
    # pos0 has inv=0, always_zero_b0 have inv in {1,2,3}
    pos4 = [p for p in not_zero_b1 if p != pos0 and p not in always_zero_b0]
    if len(pos4) == 1:
        inv_perm[pos4[0]] = 4
    else:
        # Fallback: find via block 2 constant = 100 ('d' from "data=")
        for p, v in const_b2.items():
            if v == 100 and inv_perm[p] is None:
                inv_perm[p] = 4
                break

    # From block 2 constants: 116='t'->inv 6, 61='='->inv 8, 97='a'->inv 5 or 7
    for p, v in const_b2.items():
        if v == 116 and inv_perm[p] is None:
            inv_perm[p] = 6; break
    for p, v in const_b2.items():
        if v == 61 and inv_perm[p] is None:
            inv_perm[p] = 8; break

    # Two positions with const 97 -> inv 5 and 7
    aa = [p for p, v in const_b2.items() if v == 97 and inv_perm[p] is None]
    if len(aa) >= 2:
        # Distinguish using block 3 unique value count (more unique = earlier in value)
        uniq = {p: len(set(dec[i*FRAME + 3*BLK + p] for i in range(NUM))) for p in aa}
        s = sorted(aa, key=lambda p: -uniq[p])
        inv_perm[s[0]] = 5
        inv_perm[s[1]] = 7
    elif len(aa) == 1:
        inv_perm[aa[0]] = 5 if 5 not in set(inv_perm) else 7

    # Assign {1,2,3} to always_zero_b0 positions (tentative order)
    pos123 = [p for p in always_zero_b0 if inv_perm[p] is None][:3]
    for i, p in enumerate(sorted(pos123)):
        inv_perm[p] = i + 1


    # === PHASE 5: Brute-force remaining positions using seq/hash validation ===
    # Remaining: positions in always_zero_b1 not yet assigned -> inv in {9..15}
    # Plus resolve correct order of {1,2,3} and {5,7}
    
    # Identify groups
    pos_group_123 = sorted([p for p in range(BLK) if inv_perm[p] in (1,2,3)])
    pos_group_57 = sorted([p for p in range(BLK) if inv_perm[p] in (5,7)])
    pos_group_rest = sorted([p for p in range(BLK) if inv_perm[p] is None])
    vals_rest = sorted(set(range(BLK)) - set(v for v in inv_perm if v is not None))

    # Combined brute-force: 3! * 2! * 7! = 60480 (fast enough)
    best_inv = None
    best_score = -1
    CHECK_FRAMES = [0, 1, 2, 3, 4]

    for pa in iterperms([1,2,3]):
        for pb in iterperms([5,7]):
            for pc in iterperms(vals_rest):
                trial = inv_perm[:]
                for p, v in zip(pos_group_123, pa): trial[p] = v
                for p, v in zip(pos_group_57, pb): trial[p] = v
                for p, v in zip(pos_group_rest, pc): trial[p] = v

                score = 0
                for fi in CHECK_FRAMES:
                    orig = bytearray(FRAME)
                    for bs in range(0, FRAME, BLK):
                        for p in range(BLK):
                            orig[bs + trial[p]] = dec[fi*FRAME + bs + p]
                    v = orig[36:128].split(b'\x00')[0]
                    try:
                        vs = v.decode('ascii')
                        if f"seq={fi:04d}" in vs and "hash=" in vs:
                            score += 1
                        else:
                            break
                    except:
                        break

                if score > best_score:
                    best_score = score
                    best_inv = trial[:]
                if score == len(CHECK_FRAMES):
                    break
            if best_score == len(CHECK_FRAMES): break
        if best_score == len(CHECK_FRAMES): break

    if best_inv:
        inv_perm = best_inv


    # === PHASE 6: Apply inverse permutation and output ===
    restored = bytearray(len(dec))
    for blk_start in range(0, len(dec), BLK):
        for p in range(BLK):
            restored[blk_start + inv_perm[p]] = dec[blk_start + p]

    records = []
    for fi in range(NUM):
        off = fi * FRAME
        rec_id = struct.unpack_from('<I', restored, off)[0]
        k = restored[off+4:off+36].split(b'\x00')[0].decode('utf-8', errors='replace')
        v = restored[off+36:off+128].split(b'\x00')[0].decode('utf-8', errors='replace')
        records.append({"id": rec_id, "key": k, "value": v})

    records.sort(key=lambda r: r["id"])

    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/recovered.json", "w") as f:
        json.dump(records, f, indent=2)

    print(f"Recovered {len(records)} records")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
