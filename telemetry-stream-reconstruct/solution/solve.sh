#!/bin/bash
# Recover plaintext from obfuscated telemetry stream

echo "=== Telemetry Stream Recovery ==="
echo "Analyzing /app/telemetry.bin..."
ls -la /app/telemetry.bin
echo ""

echo "File size check:"
wc -c /app/telemetry.bin
echo ""

echo "Creating recovery script..."

cat << 'PYEOF' > /tmp/recover.py
import struct
import hashlib
import json
import os

FRAME_SIZE = 64
BLOCK_SIZE = 16
NUM_FRAMES = 300
XOR_KEY_SIZE = 32

# Header formula: byte[i] = (seq * MULT[i] + OFF[i]) % 256
MULTIPLIERS = [1, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]
OFFSETS = [0, 100, 200, 50, 150, 75, 125, 175, 225, 25, 60, 90, 110, 130, 160, 190]


def build_header(seq):
    """Compute the 16-byte header for a given sequence number."""
    return bytes((seq * m + o) % 256 for m, o in zip(MULTIPLIERS, OFFSETS))


def load_frames(path):
    """Load encrypted frames from binary file."""
    with open(path, 'rb') as f:
        data = f.read()
    assert len(data) == NUM_FRAMES * FRAME_SIZE
    return [data[i*FRAME_SIZE:(i+1)*FRAME_SIZE] for i in range(NUM_FRAMES)]

PYEOF

cat << 'PYEOF' >> /tmp/recover.py

def recover_permutation(frames):
    """
    Recover the 16-byte block permutation using XOR-difference fingerprinting.
    
    Key insight: XOR-cancelling two encrypted frames eliminates the XOR key,
    leaving only the XOR of their permuted plaintexts. Since each header byte
    has a unique linear relationship to the sequence number, each input position
    produces a unique fingerprint of XOR differences across frame pairs.
    """
    # Build expected fingerprints for each input position
    test_js = [1, 2, 3, 5, 10, 50, 100, 200, 255, 299]
    input_fps = {}
    for v in range(BLOCK_SIZE):
        h0 = build_header(0)[v]
        fp = tuple(h0 ^ build_header(j)[v] for j in test_js)
        input_fps[v] = fp

    # Match each output position to its input position
    perm = [None] * BLOCK_SIZE
    for k in range(BLOCK_SIZE):
        observed = tuple(frames[0][k] ^ frames[j][k] for j in test_js)
        for v in range(BLOCK_SIZE):
            if input_fps[v] == observed:
                perm[k] = v
                break

    assert None not in perm, "Failed to recover complete permutation"
    assert sorted(perm) == list(range(BLOCK_SIZE)), "Invalid permutation"
    return perm

PYEOF

cat << 'PYEOF' >> /tmp/recover.py

def recover_xor_key(frames, perm):
    """
    Recover the 32-byte XOR key.
    
    Bytes 0-15: from block 0 using known header values.
      enc[k] = header[perm[k]] ^ xor_key[k]
      => xor_key[k] = enc[k] ^ header[perm[k]]
    
    Bytes 16-31: from block 3 (all-zero padding).
      Permuting zeros gives zeros, so enc[48+k] = xor_key[16+k]
    """
    h0 = build_header(0)
    key_0_15 = [frames[0][k] ^ h0[perm[k]] for k in range(BLOCK_SIZE)]
    key_16_31 = [frames[0][48 + k] for k in range(BLOCK_SIZE)]
    return bytes(key_0_15 + key_16_31)

PYEOF

cat << 'PYEOF' >> /tmp/recover.py

def decrypt_frame(enc, perm, xor_key):
    """Decrypt a single frame by undoing XOR then undoing permutation."""
    # Undo XOR key
    permuted = bytearray(FRAME_SIZE)
    for i in range(FRAME_SIZE):
        permuted[i] = enc[i] ^ xor_key[i % XOR_KEY_SIZE]
    # Undo permutation: since out[i] = block[perm[i]],
    # we have block[perm[i]] = permuted[i] for each block
    plaintext = bytearray(FRAME_SIZE)
    for blk in range(0, FRAME_SIZE, BLOCK_SIZE):
        for i in range(BLOCK_SIZE):
            plaintext[blk + perm[i]] = permuted[blk + i]
    return bytes(plaintext)


def main():
    print("Loading encrypted frames...")
    frames = load_frames('/app/telemetry.bin')
    print(f"  Loaded {len(frames)} frames of {FRAME_SIZE} bytes each")

    print("Recovering permutation via XOR-difference fingerprinting...")
    perm = recover_permutation(frames)
    print(f"  Permutation: {perm}")

    print("Recovering XOR key...")
    xor_key = recover_xor_key(frames, perm)
    print(f"  Key length: {len(xor_key)} bytes")

    print("Decrypting all frames...")
    all_plaintext = bytearray()
    for i in range(NUM_FRAMES):
        pt = decrypt_frame(frames[i], perm, xor_key)
        all_plaintext.extend(pt)

    # Write recovered plaintext
    output_path = '/app/recovered.bin'
    with open(output_path, 'wb') as f:
        f.write(all_plaintext)

    h = hashlib.sha256(all_plaintext).hexdigest()
    print(f"  Output: {output_path} ({len(all_plaintext)} bytes)")
    print(f"  SHA256: {h}")

    # Verify first few frames
    print("Verifying recovered headers...")
    ok = 0
    for i in range(NUM_FRAMES):
        expected_header = build_header(i)
        recovered_header = all_plaintext[i*FRAME_SIZE:i*FRAME_SIZE+BLOCK_SIZE]
        if recovered_header == expected_header:
            ok += 1
    print(f"  Header verification: {ok}/{NUM_FRAMES} correct")

    # Verify zero padding
    pad_ok = 0
    for i in range(NUM_FRAMES):
        padding = all_plaintext[i*FRAME_SIZE+48:i*FRAME_SIZE+64]
        if padding == b'\x00' * 16:
            pad_ok += 1
    print(f"  Padding verification: {pad_ok}/{NUM_FRAMES} correct")
    print("Done.")


if __name__ == '__main__':
    main()
PYEOF


echo "Running recovery..."
python3 /tmp/recover.py
echo ""
echo "Recovery complete. Output at /app/recovered.bin"
