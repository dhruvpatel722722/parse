#!/bin/bash
cat > /app/recover.py << 'PYTHON'
import struct, json, os, re
from itertools import permutations as iterperms

def main():
    with open("/app/data/telemetry.bin", "rb") as f:
        data = bytearray(f.read())

    NUM, FRAME, BLK, KLEN = 250, 91, 13, 37
    STEP = KLEN  # Frames STEP apart share key alignment (since gcd(91,37)=1)
    null = b'\x00'

    # Phase 1: Find pos0 (permuted position holding ID byte 0).
    # XOR-diff between aligned frames (0 and 37) cancels the XOR key.
    # At inv_perm[p]=0: diff = id_0 ^ id_37 = 0 ^ 37 = 37.
    pos0 = None
    for p in range(BLK):
        diff = data[p] ^ data[STEP * FRAME + p]
        if diff == STEP:
            if all(data[k*STEP*FRAME + p] ^ data[p] == k*STEP
                   for k in range(1, min(6, NUM // STEP))):
                pos0 = p
                break

    # Positions constant across aligned pairs in block 0 -> inv in {1,2,3}
    always_zero_b0 = []
    for p in range(BLK):
        if p == pos0:
            continue
        if all(data[p] ^ data[k*STEP*FRAME + p] == 0
               for k in range(1, min(7, NUM // STEP))):
            always_zero_b0.append(p)

    # Phase 2: Recover XOR key from known-zero positions across multiple frames.
    # Bytes 1-3 of ID are always 0 for ids < 256. These map to always_zero_b0.
    # Using different frames gives different key offsets (since gcd(91,37)=1).
    key = bytearray(KLEN)
    key_known = [False] * KLEN

    # Frame 0: pos0 also has orig=0 (id=0)
    for p in [pos0] + always_zero_b0:
        key[p % KLEN] = data[p]
        key_known[p % KLEN] = True

    # Cycle through frames to fill all 37 key positions
    for frame_idx in range(min(KLEN, NUM)):
        frame_off = frame_idx * FRAME
        for p in always_zero_b0:
            kpos = (frame_off + p) % KLEN
            if not key_known[kpos]:
                key[kpos] = data[frame_off + p]
                key_known[kpos] = True
        if all(key_known):
            break

    # Phase 3: Decrypt
    dec = bytearray(len(data))
    for i in range(len(data)):
        dec[i] = data[i] ^ key[i % KLEN]

    # Phase 4: Recover permutation from decrypted data.
    inv_perm = [None] * BLK
    inv_perm[pos0] = 0
    for i, p in enumerate(sorted(always_zero_b0[:3])):
        inv_perm[p] = i + 1

    # Block 3 (bytes 39-51): field2 starts at byte 44, so block 3 positions 5-12
    # hold field2[0:8] = "val=NNNN". Positions 5,6,7,8 are constant: v,a,l,=
    b3_off = 3 * BLK
    const_b3 = {}
    for p in range(BLK):
        val = dec[b3_off + p]
        if all(dec[i*FRAME + b3_off + p] == val for i in range(NUM)):
            const_b3[p] = val

    for p, v in const_b3.items():
        if v == 118 and inv_perm[p] is None:
            inv_perm[p] = 5; break
    for p, v in const_b3.items():
        if v == 97 and inv_perm[p] is None:
            inv_perm[p] = 6; break
    for p, v in const_b3.items():
        if v == 108 and inv_perm[p] is None:
            inv_perm[p] = 7; break
    for p, v in const_b3.items():
        if v == 61 and inv_perm[p] is None:
            inv_perm[p] = 8; break

    # Phase 5: Brute-force remaining positions with format validation.
    pos_123 = sorted([p for p in range(BLK) if inv_perm[p] in (1, 2, 3)])
    remaining_pos = sorted([p for p in range(BLK) if inv_perm[p] is None])
    remaining_vals = sorted(set(range(BLK)) - set(v for v in inv_perm if v is not None))
    ambiguous_pos = pos_123 + remaining_pos
    ambiguous_vals = [1, 2, 3] + remaining_vals

    f1_pat = re.compile(r'^[a-z][\w-]*\.[a-z]+\.[0-9a-f]{8}$')
    f2_pat = re.compile(r'^val=\d{4}\.\d{2} ts=\d{10} chk=[0-9a-f]{12}$')

    best_inv = None
    best_score = -1
    CHECK = list(range(0, min(5 * STEP, NUM), STEP))

    for candidate in iterperms(ambiguous_vals):
        trial = inv_perm[:]
        for p, v in zip(ambiguous_pos, candidate):
            trial[p] = v
        score = 0
        for fi in CHECK:
            orig = bytearray(FRAME)
            for bs in range(0, FRAME, BLK):
                for p in range(BLK):
                    orig[bs + trial[p]] = dec[fi * FRAME + bs + p]
            f1 = orig[4:44].split(null)[0]
            f2 = orig[44:88].split(null)[0]
            try:
                f1s = f1.decode('ascii')
                f2s = f2.decode('ascii')
                if f1_pat.match(f1s) and f2_pat.match(f2s):
                    score += 1
                else:
                    break
            except:
                break
        if score > best_score:
            best_score = score
            best_inv = trial[:]
        if score == len(CHECK):
            break

    if best_inv:
        inv_perm = best_inv

    # Phase 6: Apply inverse permutation and output.
    restored = bytearray(len(dec))
    for bs in range(0, len(dec), BLK):
        for p in range(BLK):
            restored[bs + inv_perm[p]] = dec[bs + p]

    records = []
    for fi in range(NUM):
        off = fi * FRAME
        rec_id = struct.unpack_from('<I', restored, off)[0]
        f1 = restored[off+4:off+44].split(null)[0].decode('utf-8', errors='replace')
        f2 = restored[off+44:off+88].split(null)[0].decode('utf-8', errors='replace')
        records.append({"id": rec_id, "field1": f1, "field2": f2})

    records.sort(key=lambda r: r["id"])
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/recovered.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"Recovered {len(records)} records")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
