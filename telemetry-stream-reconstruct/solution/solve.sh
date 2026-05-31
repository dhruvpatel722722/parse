#!/bin/bash
# Sensor Reading Recovery Solution
echo "=== Sensor Reading Recovery ==="
ls -la /app/readings.bin
wc -c /app/readings.bin
echo ""
echo "Running recovery..."

cat > /tmp/solve.py << 'PYEOF'
import hashlib

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
# Last block at offset (RS - BS). Since key repeats every BS bytes (key_size = block_size),
# padding gives: enc[last+k] = 0 ^ key[k] = key[k] for all k
last_blk = RS - BS
key = bytes(readings[0][last_blk + k] for k in range(BS))

# Verify key is consistent across frames (padding is always zero):
for i in range(1, NR):
    test_key = bytes(readings[i][last_blk + k] for k in range(BS))
    if test_key != key:
        print(f"WARNING: key inconsistency at frame {i}")
        break
else:
    print(f"Key verified: {BS} bytes (consistent across all frames)")

# Step 3: Undo XOR on block 0 to get permuted header values
perm_pts = []
for i in range(NR):
    blk0 = bytes(readings[i][k] ^ key[k] for k in range(BS))
    perm_pts.append(blk0)

# Step 4: Fit linear functions to determine M and O for each output position
# Header byte v = (reading_index * M[v] + O[v]) % 256
# At output position k: perm_pts[i][k] = (i * M_k + O_k) % 256
M_arr = [0] * BS
O_arr = [0] * BS
for k in range(BS):
    O_k = perm_pts[0][k]
    M_k = (perm_pts[1][k] - O_k) % 256
    ok = all(perm_pts[idx][k] == (idx * M_k + O_k) % 256 for idx in range(NR))
    if not ok:
        print(f"  WARNING: linear fit failed at position {k}")
    M_arr[k] = M_k
    O_arr[k] = O_k

print(f"Discovered multipliers: {M_arr}")

# Step 5: Recover permutation by sorting M values
# Input positions are ordered by ascending M (per problem structure)
m_sorted = sorted(range(BS), key=lambda k: M_arr[k])
perm = [0] * BS
for rank, k in enumerate(m_sorted):
    perm[k] = rank
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

# Verify padding
pad_ok = sum(1 for i in range(NR)
             if all_pt[i*RS + RS - BS:(i+1)*RS] == b'\x00' * BS)
print(f"Padding check: {pad_ok}/{NR}")

# Verify headers
hdr_ok = 0
for i in range(NR):
    hdr = all_pt[i*RS:i*RS+BS]
    expected = bytes((i * M_arr[m_sorted[v]] + O_arr[m_sorted[v]]) % 256
                     for v in range(BS))
    if hdr == expected:
        hdr_ok += 1
print(f"Header check: {hdr_ok}/{NR}")

with open('/app/recovered.bin', 'wb') as f:
    f.write(all_pt)
print(f"Output: /app/recovered.bin ({len(all_pt)} bytes)")
print(f"SHA256: {hashlib.sha256(all_pt).hexdigest()}")
PYEOF

python3 /tmp/solve.py
echo ""
echo "Done."
