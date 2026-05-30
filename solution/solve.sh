#!/bin/bash
cat > /app/recover.py << 'PYTHON'
import struct, json, os, re
from itertools import permutations as iterperms

def main():
    with open("/app/data/packets.bin", "rb") as f:
        data = bytearray(f.read())

    NUM, FRAME, BLK, KLEN = 200, 128, 16, 32

    # Phase 1: Recover XOR key from all-zero blocks (bytes 96-127).
    key = bytearray(KLEN)
    for p in range(BLK):
        key[p] = data[96 + p]
        key[(16 + p) % KLEN] = data[112 + p]

    # Phase 2: Remove XOR key.
    dec = bytearray(len(data))
    for i in range(len(data)):
        dec[i] = data[i] ^ key[i % KLEN]

    # Phase 3: Classify permutation positions.
    pos0 = None
    for p in range(BLK):
        if all(dec[i * FRAME + p] == i for i in range(NUM)):
            pos0 = p
            break

    azb0 = [p for p in range(BLK)
             if p != pos0 and all(dec[i*FRAME+p] == 0 for i in range(NUM))]

    const_b2 = {}
    for p in range(BLK):
        val = dec[2*BLK + p]
        if all(dec[i*FRAME + 2*BLK + p] == val for i in range(NUM)):
            const_b2[p] = val

    # Phase 4: Assign known positions.
    inv_perm = [None] * BLK
    inv_perm[pos0] = 0

    for p, v in const_b2.items():
        if v == 116 and inv_perm[p] is None:
            inv_perm[p] = 4; break
    for p, v in const_b2.items():
        if v == 115 and inv_perm[p] is None:
            inv_perm[p] = 5; break
    for p, v in const_b2.items():
        if v == 61 and inv_perm[p] is None:
            inv_perm[p] = 6; break

    # Group A: always-zero in block 0 -> values {1,2,3}
    grp_A_pos = sorted(azb0[:3])
    grp_A_vals = [1, 2, 3]

    # Group B: constant '0' (48) in block 2 -> values {7..12}
    grp_B_pos = sorted([p for p, v in const_b2.items()
                        if v == 48 and inv_perm[p] is None])
    grp_B_vals = list(range(7, 7 + len(grp_B_pos)))

    # Group C: remaining unassigned -> values {13,14,15}
    grp_C_pos = sorted([p for p in range(BLK)
                        if inv_perm[p] is None
                        and p not in grp_A_pos
                        and p not in grp_B_pos])
    grp_C_vals = sorted(set(range(BLK)) - {0, 4, 5, 6}
                        - set(grp_A_vals) - set(grp_B_vals))

    # Phase 5: Brute-force with format validation.
    pay_pat = re.compile(r'^ts=\d{12} len=\d{5} sig=[0-9a-f]{24}$')
    src_pat = re.compile(r'^[a-z]+\.[a-z]+\.[0-9a-f]{8}$')
    null = b'\x00'

    best_inv = None
    best_score = -1
    CHECK = [0, 1, 2, 3, 4]

    for pa in iterperms(grp_A_vals):
        for pb in iterperms(grp_B_vals):
            for pc in iterperms(grp_C_vals):
                trial = inv_perm[:]
                for p, v in zip(grp_A_pos, pa): trial[p] = v
                for p, v in zip(grp_B_pos, pb): trial[p] = v
                for p, v in zip(grp_C_pos, pc): trial[p] = v

                score = 0
                for fi in CHECK:
                    orig = bytearray(FRAME)
                    for bs in range(0, FRAME, BLK):
                        for p in range(BLK):
                            orig[bs + trial[p]] = dec[fi*FRAME + bs + p]
                    pay = orig[36:124].split(null)[0]
                    src = orig[4:36].split(null)[0]
                    try:
                        ps = pay.decode('ascii')
                        ss = src.decode('ascii')
                        if pay_pat.match(ps) and src_pat.match(ss):
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
            if best_score == len(CHECK): break
        if best_score == len(CHECK): break

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
        src = restored[off+4:off+36].split(null)[0].decode('utf-8', errors='replace')
        pay = restored[off+36:off+124].split(null)[0].decode('utf-8', errors='replace')
        records.append({"id": rec_id, "source": src, "payload": pay})

    records.sort(key=lambda r: r["id"])
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/recovered.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"Recovered {len(records)} records")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
