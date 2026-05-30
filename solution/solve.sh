#!/bin/bash
cat > /app/recover.py << 'PYTHON'
import struct, json, os

def rotate_right_byte(b, n):
    """Rotate a single byte right by n bits."""
    n = n % 8
    return ((b >> n) | (b << (8 - n))) & 0xFF

def main():
    with open("/app/data/cipher_log.bin", "rb") as f:
        data = bytearray(f.read())

    NUM_RECORDS = 150
    RECORD_SIZE = 64
    CHUNK_SIZE = 8

    # === Step 1: Undo positional bit-rotation ===
    # Each 8-byte chunk was rotated left by (chunk_index * 5 + 3) % 8 bits.
    # To undo: rotate right by the same amount.
    num_chunks = len(data) // CHUNK_SIZE
    unrotated = bytearray(len(data))
    for c in range(num_chunks):
        rot = (c * 5 + 3) % 8
        for b in range(CHUNK_SIZE):
            unrotated[c * CHUNK_SIZE + b] = rotate_right_byte(data[c * CHUNK_SIZE + b], rot)

    # === Step 2: De-interleave record pairs ===
    # Pairs of 64-byte records were interleaved byte-by-byte into 128-byte blocks.
    # block[2*i] = recordA[i], block[2*i+1] = recordB[i]
    records = []
    num_pairs = NUM_RECORDS // 2
    for pair_idx in range(num_pairs):
        block = unrotated[pair_idx * 128:(pair_idx + 1) * 128]
        rec_a = bytearray(RECORD_SIZE)
        rec_b = bytearray(RECORD_SIZE)
        for i in range(RECORD_SIZE):
            rec_a[i] = block[2 * i]
            rec_b[i] = block[2 * i + 1]
        records.append(rec_a)
        records.append(rec_b)

    # === Step 3: Parse records and output JSON ===
    result = []
    for rec in records:
        seq_id = struct.unpack_from('<I', rec, 0)[0]
        cat = rec[4:12].split(b'\x00')[0].decode('utf-8')
        msg = rec[12:60].split(b'\x00')[0].decode('utf-8')
        result.append({"id": seq_id, "category": cat, "message": msg})

    result.sort(key=lambda r: r["id"])

    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/recovered.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Recovered {len(result)} records")

if __name__ == "__main__":
    main()
PYTHON

python /app/recover.py
