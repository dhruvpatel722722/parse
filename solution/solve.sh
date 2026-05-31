#!/bin/bash
cat > /app/solver.py << 'PYTHON'
import struct
import os

def int_to_bits(value, num_bits):
    return [(value >> (num_bits - 1 - i)) & 1 for i in range(num_bits)]

def bits_to_int(bits):
    val = 0
    for b in bits:
        val = (val << 1) | b
    return val

def crc8_from_int(data_11bit, poly):
    crc = 0x00
    for i in range(10, -1, -1):
        bit = (data_11bit >> i) & 1
        crc ^= (bit << 7)
        if crc & 0x80:
            crc = ((crc << 1) ^ poly) & 0xFF
        else:
            crc = (crc << 1) & 0xFF
    return crc

def next_key(raw_int):
    rotated = ((raw_int << 7) | (raw_int >> 12)) & 0x7FFFF
    return rotated ^ 0x35A1F

def decode_signed_5bit(val):
    if val & 0x10:
        return val - 32
    return val

def main():
    with open("/app/data/telemetry.bin", "rb") as f:
        data = f.read()

    assert data[:4] == b"SMLG"
    num_records = struct.unpack(">H", data[4:6])[0]
    num_channels = data[6]

    body_bits = []
    for byte in data[8:]:
        body_bits.extend(int_to_bits(byte, 8))

    RECORD_BITS = 19
    SYNC_PATTERN = 0x55555

    # Extract first 10 scrambled record chunks
    chunks = [bits_to_int(body_bits[r*RECORD_BITS:(r+1)*RECORD_BITS]) for r in range(10)]

    # Discover CRC polynomial and initial XOR key
    best_poly = None
    best_key0 = None
    best_valid_count = 0

    for poly in range(256):
        crc_table = [crc8_from_int(d, poly) for d in range(2048)]

        for d0 in range(2048):
            raw0 = (d0 << 8) | crc_table[d0]
            k0 = chunks[0] ^ raw0

            valid_count = 1
            key = next_key(raw0)

            for r in range(1, 10):
                raw_r = chunks[r] ^ key
                data_r = (raw_r >> 8) & 0x7FF
                crc_r = raw_r & 0xFF
                if crc_table[data_r] == crc_r:
                    valid_count += 1
                key = next_key(raw_r)

            if valid_count >= 7 and valid_count > best_valid_count:
                best_valid_count = valid_count
                best_poly = poly
                best_key0 = k0

    # Decode all records
    channel_states = [0] * num_channels
    pos = 0
    rolling_key = best_key0
    records_processed = 0

    while records_processed < num_records and pos + RECORD_BITS <= len(body_bits):
        chunk_int = bits_to_int(body_bits[pos:pos + RECORD_BITS])
        if chunk_int == SYNC_PATTERN:
            pos += RECORD_BITS
            continue

        raw_int = chunk_int ^ rolling_key
        data_11 = (raw_int >> 8) & 0x7FF
        crc_val = raw_int & 0xFF
        expected_crc = crc8_from_int(data_11, best_poly)

        if expected_crc == crc_val:
            channel_id = (data_11 >> 5) & 0x3F
            delta_raw = data_11 & 0x1F
            delta = decode_signed_5bit(delta_raw)
            channel_states[channel_id] = (channel_states[channel_id] + delta) % 256

        rolling_key = next_key(raw_int)
        records_processed += 1
        pos += RECORD_BITS

    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/channel_states.txt", "w") as f:
        for state in channel_states:
            f.write(f"{state}\n")

    print(f"Decoded {records_processed} records, poly={hex(best_poly)}, key0={hex(best_key0)}")

if __name__ == "__main__":
    main()
PYTHON

python /app/solver.py
