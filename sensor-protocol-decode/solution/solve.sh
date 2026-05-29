#!/bin/bash
cat > /app/decode.py << 'PYTHON'
import struct
import json
import os

def decode_capture():
    with open("/app/data/capture.bin", "rb") as f:
        data = f.read()
    
    pos = 0
    packet_number = 0
    sensors = {}
    checksum_failures = 0
    total_packets = 0
    
    while pos < len(data):
        # Read magic
        if pos + 2 > len(data):
            break
        magic = data[pos:pos+2]
        if magic != b'\xFE\xED':
            break
        pos += 2
        
        # Read type
        ptype = data[pos]
        pos += 1
        
        # Read length
        length = struct.unpack_from('>H', data, pos)[0]
        pos += 2
        
        # Read payload
        payload_enc = data[pos:pos+length]
        pos += length
        
        # Read checksum
        checksum_expected = data[pos]
        pos += 1
        
        total_packets += 1
        
        # Verify checksum
        checksum_actual = 0
        for b in payload_enc:
            checksum_actual ^= b
        
        if checksum_actual != checksum_expected:
            checksum_failures += 1
            packet_number += 1
            continue
        
        # Skip heartbeats
        if ptype == 0x02:
            packet_number += 1
            continue
        
        # Decrypt data payload
        key = (packet_number * 37 + 13) & 0xFF
        payload_plain = bytes(b ^ key for b in payload_enc)
        
        # Parse: 2-byte sensor ID + 4-byte floats
        sensor_id = struct.unpack_from('>H', payload_plain, 0)[0]
        num_floats = (len(payload_plain) - 2) // 4
        
        sid_str = str(sensor_id)
        if sid_str not in sensors:
            sensors[sid_str] = {"readings": []}
        
        for i in range(num_floats):
            val = struct.unpack_from('>f', payload_plain, 2 + i*4)[0]
            sensors[sid_str]["readings"].append(round(val, 2))
        
        packet_number += 1
    
    # Compute stats
    for sid_str, sdata in sensors.items():
        r = sdata["readings"]
        sdata["avg"] = round(sum(r) / len(r), 2)
        sdata["min"] = round(min(r), 2)
        sdata["max"] = round(max(r), 2)
    
    result = {
        "sensors": sensors,
        "total_packets": total_packets,
        "checksum_failures": checksum_failures,
    }
    
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/readings.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Decoded {total_packets} packets, {checksum_failures} checksum failures")
    print(f"Sensors: {len(sensors)}")

if __name__ == "__main__":
    decode_capture()
PYTHON

python /app/decode.py
