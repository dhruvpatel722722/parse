#!/bin/bash
echo "=== Scrambled Record Recovery ==="
ls -la /app/data.bin
wc -c /app/data.bin
echo ""
echo "Running recovery..."

cat > /tmp/solve.py << 'PYEOF'
import hashlib

KNOWN_MULT = [23, 1, 41, 7, 31, 11, 3, 37, 29, 13, 19, 17]

with open('/app/data.bin', 'rb') as f:
    raw = f.read()

RS = 96
NR = len(raw) // RS
records = [raw[i*RS:(i+1)*RS] for i in range(NR)]
print(f"Loaded {NR} records x {RS} bytes")

# Discover block size: find always-zero diff positions and their periodicity
always_zero = set(range(RS))
for j in range(1, NR):
    for k in range(RS):
        if records[0][k] ^ records[j][k] != 0:
            always_zero.discard(k)

for bs in [6, 8, 12, 16, 24]:
    residues = set(p % bs for p in always_zero)
    if len(residues) > 0 and len(always_zero) == (RS // bs) * len(residues):
        BS = bs
        break
else:
    BS = 12
print(f"Block size: {BS}")

# Recover XOR key from last block (padding = 0x00)
last_blk = RS - BS
key = bytes(records[0][last_blk + k] for k in range(BS))
for i in range(1, NR):
    if bytes(records[i][last_blk + k] for k in range(BS)) != key:
        print(f"Key inconsistency at record {i}!")
        break
else:
    print(f"Key recovered: {BS} bytes")

# Undo XOR on block 0 of record 0 to get permuted offsets
perm_hdr0 = bytes(records[0][k] ^ key[k] for k in range(BS))

# Fit linear functions to discover M values per output position
perm_pts = [bytes(records[i][k] ^ key[k] for k in range(BS)) for i in range(NR)]
M_arr = [(perm_pts[1][k] - perm_pts[0][k]) % 256 for k in range(BS)]
print(f"Discovered M: {M_arr}")

# Recover permutation by matching M values to known MULT array
perm = [None] * BS
for k in range(BS):
    for v in range(BS):
        if KNOWN_MULT[v] == M_arr[k]:
            perm[k] = v
            break
print(f"Permutation: {perm}")

# Decrypt all records
def decrypt(enc):
    permuted = bytearray(RS)
    for i in range(RS):
        permuted[i] = enc[i] ^ key[i % BS]
    pt = bytearray(RS)
    for blk in range(0, RS, BS):
        for i in range(BS):
            pt[blk + perm[i]] = permuted[blk + i]
    return bytes(pt)

all_pt = b''.join(decrypt(records[i]) for i in range(NR))
pad_ok = sum(1 for i in range(NR) if all_pt[i*RS+RS-BS:(i+1)*RS] == b'\x00'*BS)
print(f"Padding check: {pad_ok}/{NR}")

with open('/app/recovered.bin', 'wb') as f:
    f.write(all_pt)
print(f"Output: /app/recovered.bin ({len(all_pt)} bytes)")
print(f"SHA256: {hashlib.sha256(all_pt).hexdigest()}")
PYEOF

python3 /tmp/solve.py
echo ""
echo "Done."
