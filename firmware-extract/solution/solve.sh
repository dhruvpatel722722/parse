#!/bin/bash
cat > /app/extract.py << 'PYTHON'
import struct
import json
import os

def main():
    with open("/app/data/firmware.bin", "rb") as f:
        firmware = f.read()
    
    # Parse header
    magic = firmware[0:4]
    assert magic == b'\xFE\xED\xFA\xCE', f"Bad magic: {magic.hex()}"
    
    # Master key at offset 16 (16 bytes)
    master_key = firmware[16:32]
    
    # Config offset and sizes at bytes 32-43
    config_offset = struct.unpack_from('<I', firmware, 32)[0]
    config_enc_size = struct.unpack_from('<I', firmware, 36)[0]
    config_orig_size = struct.unpack_from('<I', firmware, 40)[0]
    
    # Extract encrypted blob
    blob = bytearray(firmware[config_offset:config_offset + config_enc_size])
    
    # Reverse Layer 3: Un-swap adjacent byte pairs
    unswapped = bytearray(len(blob))
    for i in range(0, len(blob) - 1, 2):
        unswapped[i] = blob[i+1]
        unswapped[i+1] = blob[i]
    if len(blob) % 2 == 1:
        unswapped[-1] = blob[-1]
    
    # Reverse Layer 2: Rotate each 8-byte block RIGHT by (block_index % 5)
    unrotated = bytearray(len(unswapped))
    for block_idx in range(len(unswapped) // 8):
        block = unswapped[block_idx*8:(block_idx+1)*8]
        shift = block_idx % 5
        # Reverse of left rotation by N is right rotation by N
        unrotated_block = block[8-shift:] + block[:8-shift]
        unrotated[block_idx*8:(block_idx+1)*8] = unrotated_block
    
    # Reverse Layer 1: XOR with repeating master key
    decrypted = bytearray(len(unrotated))
    for i in range(len(unrotated)):
        decrypted[i] = unrotated[i] ^ master_key[i % 16]
    
    # Trim to original size and parse
    config_bytes = decrypted[:config_orig_size]
    config = json.loads(config_bytes.decode('utf-8'))
    
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/config.json", "w") as f:
        json.dump(config, f, separators=(',', ':'))
    
    print(f"Extracted config: {len(config_bytes)} bytes")
    print(f"Device: {config.get('device_id')}")

if __name__ == "__main__":
    main()
PYTHON

python /app/extract.py
