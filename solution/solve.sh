#!/bin/bash
# Sensor Reading Recovery Solution
echo "=== Sensor Reading Recovery ==="
ls -la /app/readings.bin
wc -c /app/readings.bin
echo ""
echo "Running recovery..."

cat > /tmp/solve.py << 'PYEOF'
import hashlib

KNOWN_MULT = [23, 1, 41, 7, 31, 11, 3, 37, 29, 13, 19, 17]

with open('/app/readings.bin', 'rb') as f:
    raw = f.read()

RS = 96
NR = len(raw) // RS
readings = [raw[i*RS:(i+1)*RS] for i in range(NR)]
print(f"Loaded {NR} readings x {RS} bytes")

# Step 1: Discover block size via periodicity of constant-diff positions
always_zero = set(range(RS))
for j in range(1, NR):
    for k in range(RS):
        if readings[0][k] ^ readings[j][k] != 0:
            always_zero.discard(k)

for bs in [6, 8, 12, 16, 24]:
    residues = set(p % bs for p in always_zero)
    if len(residues) > 0 and len(always_zero) == (RS // bs) * len(residues):
        BS = bs
        break
else:
    BS = 12
print(f"Block size: {BS}")

# Step 2: Recover XOR key from last block (all-zero padding)
last_blk = RS - BS
key = bytes(readings[0][last_blk + k] for k in range(BS))

# Verify key consistency across frames
for i in range(1, NR):
    if bytes(readings[i][last_blk + k] for k in range(BS)) != key:
        print(f"Key inconsistency at frame {i}!")
        break
else:
    print(f"Key recovered: {BS} bytes")

# Step 3: Undo XOR on block 0 to get permuted header values
perm_pts = []
for i in range(NR):
    blk0 = bytes(readings[i][k] ^ key[k] for k in range(BS))
    perm_pts.append(blk0)

# Step 4: Fit linear functions per output position
M_arr = [0] * BS
O_arr = [0] * BS
for k in range(BS):
    O_k = perm_pts[0][k]
    M_k = (perm_pts[1][k] - O_k) % 256
    ok = all(perm_pts[idx][k] == (idx * M_k + O_k) % 256 for idx in range(NR))
    if not ok:
        print(f"  Linear fit failed at position {k}")
    M_arr[k] = M_k
    O_arr[k] = O_k

print(f"Discovered M values: {M_arr}")

# Step 5: Recover permutation using known MULT array
# perm[k] = index v in KNOWN_MULT where KNOWN_MULT[v] == M_arr[k]
perm = [None] * BS
for k in range(BS):
    for v in range(BS):
        if KNOWN_MULT[v] == M_arr[k]:
            perm[k] = v
            break
    if perm[k] is None:
        print(f"  ERROR: M={M_arr[k]} not found in MULT array")

print(f"Permutation: {perm}")

# Step 6: Decrypt all readings
def decrypt(enc):
    permuted = bytearray(RS)
    for i in range(RS):
        permuted[i] = enc[i] ^ key[i % BS]
    pt = bytearray(RS)
    for blk in range(0, RS, BS):
        for i in range(BS):
            pt[blk + perm[i]] = permuted[blk + i]
    return bytes(pt)

all_pt = b''.join(decrypt(readings[i]) for i in range(NR))

# Verify
pad_ok = sum(1 for i in range(NR)
             if all_pt[i*RS+RS-BS:(i+1)*RS] == b'\x00'*BS)
print(f"Padding check: {pad_ok}/{NR}")

with open('/app/recovered.bin', 'wb') as f:
    f.write(all_pt)
print(f"Output: /app/recovered.bin ({len(all_pt)} bytes)")
print(f"SHA256: {hashlib.sha256(all_pt).hexdigest()}")
PYEOF

python3 /tmp/solve.py
echo ""
echo "Done."
