#!/usr/bin/env python3
"""Generate a fake firmware image with triple-encrypted config table."""
import os
import struct
import json
import random
import hashlib

random.seed(54321)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# The config data to hide
config = {
    "device_id": "IOT-7B3F-9A2E-4D1C",
    "sensors": [
        {"name": "temperature", "pin": 4, "calibration": -0.32},
        {"name": "humidity", "pin": 7, "calibration": 1.05},
        {"name": "pressure", "pin": 12, "calibration": 0.0},
        {"name": "light", "pin": 15, "calibration": -2.1},
        {"name": "co2", "pin": 22, "calibration": 0.78},
    ],
    "network": {
        "ssid": "IndustrialNet-5G",
        "gateway": "10.0.50.1",
        "dns": "10.0.50.2",
    },
    "version": "3.7.1-rc2",
}

config_json = json.dumps(config, separators=(',', ':')).encode('utf-8')

# Master encryption key (16 bytes) - stored in header
MASTER_KEY = bytes([0x4A, 0xB7, 0x23, 0xDE, 0x91, 0x5F, 0x68, 0xC4,
                    0x3E, 0xA0, 0x17, 0x82, 0xF5, 0x6B, 0xD9, 0x04])

# Build firmware image (64KB)
firmware = bytearray(65536)

# Fill with pseudo-random noise (simulates code/data sections)
for i in range(65536):
    firmware[i] = (i * 7 + 0x5A) & 0xFF

# --- HEADER (first 256 bytes) ---
# Bytes 0-3: firmware magic 0xFE ED FA CE
firmware[0:4] = b'\xFE\xED\xFA\xCE'
# Bytes 4-7: firmware version
struct.pack_into('<I', firmware, 4, 0x00030701)
# Bytes 8-11: total size
struct.pack_into('<I', firmware, 8, 65536)
# Bytes 12-15: header checksum placeholder
# Bytes 16-31: master key (the agent must find this!)
firmware[16:32] = MASTER_KEY
# Bytes 32-35: config table offset
CONFIG_OFFSET = 4096  # placed at 4KB into firmware
struct.pack_into('<I', firmware, 32, CONFIG_OFFSET)
# Bytes 36-39: config table size (size AFTER all encryption, which equals original size + padding)
# Pad config to multiple of 8 for block operations
padded_len = len(config_json)
if padded_len % 8 != 0:
    padded_len += 8 - (padded_len % 8)
config_padded = config_json + b'\x00' * (padded_len - len(config_json))
struct.pack_into('<I', firmware, 36, padded_len)
# Bytes 40-43: original (unpadded) config size
struct.pack_into('<I', firmware, 40, len(config_json))

# --- ENCRYPT CONFIG (3 layers) ---
# Layer 1: XOR with repeating master key
encrypted = bytearray(len(config_padded))
for i in range(len(config_padded)):
    encrypted[i] = config_padded[i] ^ MASTER_KEY[i % 16]

# Layer 2: Rotate each 8-byte block left by (block_index % 5)
rotated = bytearray(len(encrypted))
for block_idx in range(len(encrypted) // 8):
    block = encrypted[block_idx*8:(block_idx+1)*8]
    shift = block_idx % 5
    rotated_block = block[shift:] + block[:shift]
    rotated[block_idx*8:(block_idx+1)*8] = rotated_block

# Layer 3: Swap adjacent byte pairs
swapped = bytearray(len(rotated))
for i in range(0, len(rotated) - 1, 2):
    swapped[i] = rotated[i+1]
    swapped[i+1] = rotated[i]
if len(rotated) % 2 == 1:
    swapped[-1] = rotated[-1]

# Place encrypted config in firmware
firmware[CONFIG_OFFSET:CONFIG_OFFSET+len(swapped)] = swapped

# Write firmware
with open("/app/data/firmware.bin", "wb") as f:
    f.write(firmware)

# Write reference
with open("/app/data/.reference.json", "w") as f:
    json.dump(config, f, separators=(',', ':'))

print(f"Firmware: {len(firmware)} bytes")
print(f"Config at offset {CONFIG_OFFSET}, encrypted size {padded_len}, original {len(config_json)}")
print(f"Master key at offset 16")
