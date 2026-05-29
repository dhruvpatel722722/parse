#!/usr/bin/env python3
"""Generate a binary capture file with a custom proprietary protocol.

Protocol:
- Magic: 0xFE ED (2 bytes, big-endian)
- Type: 1 byte (0x01=data, 0x02=heartbeat)
- Length: 2 bytes big-endian (payload length)
- Payload: variable length
- Checksum: 1 byte XOR of all payload bytes

Data payloads are encrypted: each byte XORed with key = (packet_number * 37 + 13) & 0xFF
After decryption: 2-byte BE sensor_id + sequence of 4-byte BE IEEE754 floats

Some packets have intentionally corrupted checksums.
"""
import os
import struct
import json
import random
import math

random.seed(98765)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

MAGIC = b'\xFE\xED'
TYPE_DATA = 0x01
TYPE_HEARTBEAT = 0x02

NUM_SENSORS = 8
SENSOR_IDS = [0x0100 + i for i in range(NUM_SENSORS)]  # 256, 257, ..., 263

# Generate readings for each sensor
sensor_readings = {}
for sid in SENSOR_IDS:
    base = random.uniform(15.0, 85.0)
    readings = [round(base + random.gauss(0, 3.0), 2) for _ in range(random.randint(12, 25))]
    sensor_readings[sid] = readings

# Build packet stream
packets = []
packet_number = 0
checksum_failures = 0

# Interleave data and heartbeat packets
reading_indices = {sid: 0 for sid in SENSOR_IDS}

for round_num in range(30):
    # Some heartbeats
    if random.random() < 0.3:
        payload = struct.pack('>I', round_num)  # heartbeat payload = round counter
        packets.append((TYPE_HEARTBEAT, payload, packet_number, False))
        packet_number += 1
    
    # Data packets from random sensors
    sensors_this_round = random.sample(SENSOR_IDS, random.randint(2, 5))
    for sid in sensors_this_round:
        idx = reading_indices[sid]
        readings = sensor_readings[sid]
        if idx >= len(readings):
            continue
        
        # Pack 1-4 readings per packet
        num_readings = min(random.randint(1, 4), len(readings) - idx)
        payload_plain = struct.pack('>H', sid)
        for r in readings[idx:idx+num_readings]:
            payload_plain += struct.pack('>f', r)
        reading_indices[sid] = idx + num_readings
        
        # Occasionally corrupt the checksum
        corrupt = random.random() < 0.08
        if corrupt:
            checksum_failures += 1
        
        packets.append((TYPE_DATA, payload_plain, packet_number, corrupt))
        packet_number += 1

# Serialize to binary
capture = bytearray()
for ptype, payload_plain, pkt_num, corrupt in packets:
    # Encrypt data payloads
    if ptype == TYPE_DATA:
        key = (pkt_num * 37 + 13) & 0xFF
        payload_enc = bytes(b ^ key for b in payload_plain)
    else:
        # Heartbeats are not encrypted
        payload_enc = payload_plain
    
    # Compute checksum on encrypted payload (what's actually in the packet)
    checksum = 0
    for b in payload_enc:
        checksum ^= b
    
    if corrupt:
        checksum ^= 0xFF  # Flip all bits to corrupt
    
    # Build packet
    pkt = MAGIC
    pkt += struct.pack('>B', ptype)
    pkt += struct.pack('>H', len(payload_enc))
    pkt += payload_enc
    pkt += struct.pack('>B', checksum)
    capture.extend(pkt)

with open("/app/data/capture.bin", "wb") as f:
    f.write(capture)

# Compute reference output (only from valid data packets)
ref_sensors = {}
valid_packets = 0
for ptype, payload_plain, pkt_num, corrupt in packets:
    if ptype == TYPE_DATA and not corrupt:
        sid = struct.unpack_from('>H', payload_plain, 0)[0]
        num_floats = (len(payload_plain) - 2) // 4
        readings = []
        for i in range(num_floats):
            val = struct.unpack_from('>f', payload_plain, 2 + i*4)[0]
            readings.append(round(val, 2))
        
        sid_str = str(sid)
        if sid_str not in ref_sensors:
            ref_sensors[sid_str] = {"readings": []}
        ref_sensors[sid_str]["readings"].extend(readings)

for sid_str, data in ref_sensors.items():
    r = data["readings"]
    data["avg"] = round(sum(r) / len(r), 2)
    data["min"] = round(min(r), 2)
    data["max"] = round(max(r), 2)

reference = {
    "sensors": ref_sensors,
    "total_packets": len(packets),
    "checksum_failures": checksum_failures,
}

with open("/app/data/.reference.json", "w") as f:
    json.dump(reference, f, indent=2)

print(f"Generated capture: {len(capture)} bytes, {len(packets)} packets")
print(f"Sensors: {len(ref_sensors)}, Checksum failures: {checksum_failures}")
