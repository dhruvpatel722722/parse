#!/bin/bash
# Sensor Reading Recovery Solution
echo "=== Sensor Reading Recovery ==="
ls -la /app/readings.bin
wc -c /app/readings.bin
echo ""
echo "Running recovery..."

cat > /tmp/solve.py << 'PYEOF'
import hashlib

KNOWN_OFF = [175, 0, 60, 100, 225, 150, 50, 10, 200, 25, 75, 125]

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

for i in range(1, NR):
    if bytes(readings[i][last_blk + k] for k in range(BS)) != key:
        print(f"Key inconsistency at frame {i}!")
        break
else:
    print(f"Key recovered: {BS} bytes")

# Step 3: Undo XOR on block 0 of frame 0 to get permuted header offsets
perm_hdr0 = bytes(readings[0][k] ^ key[k] for k in range(BS))
# perm_hdr0[k] = OFF[perm[k]] (header at reading_index=0 = just offsets)

# Step 4: Recover permutation by matching to known O array
perm = [None] * BS
for k in range(BS):
    val = perm_hdr0[k]
    for v in range(BS):
        if KNOWN_OFF[v] == val and v not in perm:
            perm[k] = v
            break
    if perm[k] is None:
        print(f"  ERROR: value {val} not found in O array")

print(f"Permutation: {perm}")

# Step 5: Decrypt all readings
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
