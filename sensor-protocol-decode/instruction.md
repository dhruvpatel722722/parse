A binary capture file at `/app/data/capture.bin` contains network traffic from a proprietary sensor protocol recorded between a sensor array and a data collector.

Write `/app/decode.py` to parse the capture, decrypt sensor readings, and produce `/app/output/readings.json`.

Output format:
```
{
  "sensors": {
    "<sensor_id>": {
      "readings": [<float>, ...],
      "avg": <float>,
      "min": <float>,
      "max": <float>
    }
  },
  "total_packets": <int>,
  "checksum_failures": <int>
}
```

What is documented about the protocol:
- Packets are concatenated with no gaps or separators
- Each packet has: 2-byte magic, 1-byte type, 2-byte BE payload length, variable payload, 1-byte checksum
- The magic is `0xFEED` (big-endian)
- Type `0x01` = data, type `0x02` = heartbeat (discard heartbeat data)
- Checksum is XOR of all payload bytes; packets with bad checksums should be counted but data discarded
- Heartbeat payloads are unencrypted
- Data payloads are encrypted with a per-packet XOR key derived from the packet's 0-indexed position in the stream
- The derivation formula is undocumented — determine it by analyzing patterns
- After decryption, data payloads contain: 2-byte BE sensor ID followed by one or more 4-byte BE IEEE 754 floats
- Sensor IDs are in the 256-263 range
- Round all floats to 2 decimal places

Hint: heartbeat packets (type 0x02) are unencrypted and help understand stream structure. The key for each data packet depends on its 0-indexed position in the full packet stream. After correct decryption, sensor IDs will be 256-263 and readings will be plausible temperatures.

Run: `python /app/decode.py`
