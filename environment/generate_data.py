#!/usr/bin/env python3
"""
Generate data for the state-machine-recovery task.

The task encodes 64-channel state machine transitions in a custom binary protocol
with multiple difficulty layers:

1. HEADER: 8 bytes - magic "SMLG" + 2-byte BE record count + 1-byte channel count + 1-byte flags
2. BODY: Records packed at 19 bits each in a continuous bitstream
   - 6 bits: channel ID (0-63)
   - 5 bits: signed delta (2's complement, -16..+15) 
   - 8 bits: CRC-8 checksum (non-standard polynomial 0xD5)
3. COMPLICATION: Every 19-bit record is XOR'd with a 19-bit rolling key
   derived from the previous record's raw bits (before XOR).
   First record uses initial key = 0x4A3E7 (19 bits).
4. SYNC MARKERS: 19 bits of pattern 0x55555 (alternating 10101...) every 50 records
   These are NOT XOR'd and are NOT records.
5. ~15% of records have corrupted CRC (after XOR layer is applied)

The agent receives:
- The binary file
- A README that describes the basic format but NOT:
  - The CRC polynomial
  - The XOR rolling key mechanism  
  - The initial key value
  
The agent must:
1. Parse the bitstream
2. Detect and handle sync markers
3. Discover the XOR key mechanism by analyzing patterns
4. Determine the CRC polynomial (by brute-forcing with unscrambled data)
5. Track state for 64 channels
6. Output final states
"""

import json
import os
import random
import struct

random.seed(54321)

NUM_CHANNELS = 64
NUM_RECORDS = 400
CORRUPT_RATE = 0.15
SYNC_INTERVAL = 50
CRC_POLY = 0xD5  # Non-standard: x^8 + x^7 + x^6 + x^4 + x^2 + 1
INITIAL_XOR_KEY = 0x4A3E7  # 19-bit initial rolling XOR key
RECORD_BITS = 19
SYNC_PATTERN = 0x55555  # 19 bits: 01010101010101010101 (alternating)


def crc8(data_bits, poly=CRC_POLY):
    """CRC-8 over a list of bits. No init, no final XOR."""
    crc = 0x00
    for bit in data_bits:
        crc ^= (bit << 7)
        if crc & 0x80:
            crc = ((crc << 1) ^ poly) & 0xFF
        else:
            crc = (crc << 1) & 0xFF
    return crc


def int_to_bits(value, num_bits):
    """Convert integer to list of bits (MSB first)."""
    return [(value >> (num_bits - 1 - i)) & 1 for i in range(num_bits)]


def bits_to_int(bits):
    """Convert list of bits (MSB first) to integer."""
    val = 0
    for b in bits:
        val = (val << 1) | b
    return val


def bits_to_bytes(bits):
    """Convert bit list to bytes, zero-padding final byte."""
    while len(bits) % 8 != 0:
        bits.append(0)
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        result.append(byte)
    return bytes(result)


def encode_delta_5bit(delta):
    """Encode signed delta (-16..+15) as 5-bit 2's complement."""
    if delta < 0:
        return (1 << 5) + delta
    return delta


def xor_bits(bits_a, bits_b):
    """XOR two bit lists of same length."""
    return [a ^ b for a, b in zip(bits_a, bits_b)]


# ============================================================================
# GENERATE RECORDS
# ============================================================================

channel_states = [0] * NUM_CHANNELS
records = []  # (channel, delta, is_corrupt)

for i in range(NUM_RECORDS):
    channel = random.randint(0, NUM_CHANNELS - 1)
    delta = random.randint(-16, 15)
    is_corrupt = random.random() < CORRUPT_RATE
    records.append((channel, delta, is_corrupt))
    if not is_corrupt:
        channel_states[channel] = (channel_states[channel] + delta) % 256

# ============================================================================
# ENCODE INTO BITSTREAM WITH XOR LAYER
# ============================================================================

bitstream = []

# Header: "SMLG" + 2-byte BE record count + 1-byte channel count + 1-byte flags
header = b"SMLG" + struct.pack(">H", NUM_RECORDS) + bytes([NUM_CHANNELS, 0x00])
for byte in header:
    bitstream.extend(int_to_bits(byte, 8))

# Encode records with XOR rolling key and sync markers
rolling_key = INITIAL_XOR_KEY  # 19-bit key

for i, (channel, delta, is_corrupt) in enumerate(records):
    # Insert sync marker every SYNC_INTERVAL records
    if i > 0 and i % SYNC_INTERVAL == 0:
        sync_bits = int_to_bits(SYNC_PATTERN, RECORD_BITS)
        bitstream.extend(sync_bits)
        # Sync markers do NOT affect the rolling key

    # Build raw record: 6-bit channel + 5-bit delta + 8-bit CRC
    channel_bits = int_to_bits(channel, 6)
    delta_encoded = encode_delta_5bit(delta)
    delta_bits = int_to_bits(delta_encoded, 5)
    data_bits = channel_bits + delta_bits  # 11 bits for CRC input
    crc_value = crc8(data_bits)

    if is_corrupt:
        # Ensure at least one bit flip survives (avoid self-cancellation)
        original_crc = crc_value
        while crc_value == original_crc:
            crc_value = original_crc
            num_flips = random.randint(1, 3)
            for _ in range(num_flips):
                flip_bit = random.randint(0, 7)
                crc_value ^= (1 << flip_bit)

    crc_bits = int_to_bits(crc_value, 8)
    raw_record_bits = channel_bits + delta_bits + crc_bits  # 19 bits

    # XOR with rolling key
    key_bits = int_to_bits(rolling_key, RECORD_BITS)
    scrambled_bits = xor_bits(raw_record_bits, key_bits)

    # Update rolling key: rotate raw record left by 7, then XOR with constant
    raw_int = bits_to_int(raw_record_bits)
    rolling_key = ((raw_int << 7) | (raw_int >> 12)) & ((1 << RECORD_BITS) - 1)
    rolling_key ^= 0x35A1F  # Mix with constant to prevent trivial shifts

    bitstream.extend(scrambled_bits)

# ============================================================================
# WRITE DATA FILES
# ============================================================================

os.makedirs("/app/data", exist_ok=True)

raw_bytes = bits_to_bytes(bitstream)
with open("/app/data/telemetry.bin", "wb") as f:
    f.write(raw_bytes)

# README - gives partial info, deliberately omits XOR layer and CRC polynomial
with open("/app/data/protocol.txt", "w") as f:
    f.write("""TELEMETRY PROTOCOL SPECIFICATION (PARTIAL)
==========================================
Version: 2.7-CLASSIFIED

HEADER (8 bytes):
  Bytes 0-3: Magic "SMLG"
  Bytes 4-5: Record count (big-endian unsigned 16-bit)
  Byte 6: Number of channels
  Byte 7: Flags (reserved)

BODY:
  Records are packed at 19 bits each in a continuous bitstream.
  The bitstream immediately follows the header with no padding.
  
  Each raw record contains:
    - Bits [0:5]   = channel_id (6 bits, unsigned)
    - Bits [6:10]  = state_delta (5 bits, signed 2's complement)
    - Bits [11:18] = integrity_check (8 bits)

  IMPORTANT: Records in the bitstream are scrambled with a rolling
  XOR cipher. Each 19-bit record is XOR'd with a 19-bit key that
  changes after every record. The next key is derived from the
  current record's unscrambled bits by rotating left 7 positions
  and XOR'ing with a fixed mask.

SYNC MARKERS:
  A 19-bit synchronization pattern (0x55555) appears between
  records at regular intervals. Sync markers are NOT scrambled
  and do NOT participate in key feedback.

INTEGRITY CHECK:
  Valid records have a correct 8-bit integrity check computed
  over the 11 data bits (channel_id + state_delta). Records
  with invalid checks are corrupted and must be skipped.
  The check algorithm is CRC-8 with a non-standard polynomial
  (no init value, no final XOR).

INITIAL STATE:
  All channel states begin at 0 and update modulo 256.

OUTPUT:
  /app/output/channel_states.txt - one decimal value per line
  for channels 0 through 63 (64 lines total).
""")

# Write reference answer
os.makedirs("/var/lib/tbench", exist_ok=True)
reference = {
    "channel_states": channel_states,
    "num_valid": sum(1 for _, _, c in records if not c),
    "num_corrupt": sum(1 for _, _, c in records if c),
}

with open("/var/lib/tbench/.reference.json", "w") as f:
    json.dump(reference, f, indent=2)

print(f"Generated {NUM_RECORDS} records ({sum(1 for _,_,c in records if not c)} valid, {sum(1 for _,_,c in records if c)} corrupt)")
print(f"Bitstream: {len(bitstream)} bits = {len(raw_bytes)} bytes")
print(f"Channel states (first 8): {channel_states[:8]}")
print(f"Reference written to /var/lib/tbench/.reference.json")
