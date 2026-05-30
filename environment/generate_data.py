#!/usr/bin/env python3
"""Generate obfuscated packet log with two-layer encoding."""
import os
import struct
import json
import random
import hashlib

random.seed(77777)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

PERM = [13, 5, 10, 1, 15, 8, 2, 4, 14, 0, 7, 6, 12, 9, 3, 11]

XOR_KEY = bytes([115, 120, 227, 187, 204, 255, 209, 39, 234, 15, 219, 203,
                 182, 221, 93, 179, 91, 27, 94, 200, 78, 89, 196, 213,
                 46, 240, 96, 225, 224, 241, 104, 79])

PROTOCOLS = ["tcp", "udp", "icmp", "dns", "http", "tls", "ssh", "ftp",
             "smtp", "ntp", "dhcp", "arp", "bgp", "ospf", "snmp", "sip"]

STATUSES = ["accepted", "rejected", "timeout", "retransmit", "redirect",
            "filtered", "proxied", "cached", "dropped", "forwarded",
            "throttled", "mirrored", "encrypted", "decrypted", "queued", "delivered"]

NUM_RECORDS = 200
FRAME_SIZE = 128
PERM_BLOCK = 16
XOR_KEY_LEN = 32

records = []
for i in range(NUM_RECORDS):
    frame = bytearray(FRAME_SIZE)
    struct.pack_into('<I', frame, 0, i)

    proto = PROTOCOLS[i % len(PROTOCOLS)]
    status = STATUSES[(i * 3 + 1) % len(STATUSES)]
    h = hashlib.md5(f"pkt-{i}".encode()).hexdigest()[:8]
    src = f"{proto}.{status}.{h}"
    src_bytes = src.encode('utf-8')[:32]
    frame[4:4+len(src_bytes)] = src_bytes

    ts = i * 1337 + 42
    chk = hashlib.sha256(f"payload-{i}".encode()).hexdigest()[:24]
    payload = f"ts={ts:012d} len={((i*7+13)%9000)+1000:05d} sig={chk}"
    pay_bytes = payload.encode('utf-8')[:88]
    frame[36:36+len(pay_bytes)] = pay_bytes

    records.append(frame)

# Save reference
reference = []
for frame in records:
    seq_id = struct.unpack_from('<I', frame, 0)[0]
    src = frame[4:36].split(b'\x00')[0].decode('utf-8')
    pay = frame[36:124].split(b'\x00')[0].decode('utf-8')
    reference.append({"id": seq_id, "source": src, "payload": pay})

os.makedirs("/var/lib/tbench", exist_ok=True)
with open("/var/lib/tbench/.reference.json", "w") as f:
    json.dump(reference, f, indent=2)

# Serialize
raw = bytearray()
for frame in records:
    raw.extend(frame)

# Layer 1: Permutation on 16-byte blocks
permuted = bytearray(len(raw))
for block_start in range(0, len(raw), PERM_BLOCK):
    block = raw[block_start:block_start + PERM_BLOCK]
    for i in range(PERM_BLOCK):
        permuted[block_start + PERM[i]] = block[i]

# Layer 2: XOR with repeating key
xored = bytearray(len(permuted))
for i in range(len(permuted)):
    xored[i] = permuted[i] ^ XOR_KEY[i % XOR_KEY_LEN]

with open("/app/data/packets.bin", "wb") as f:
    f.write(xored)

print(f"Generated {NUM_RECORDS} records, {len(xored)} bytes")
