A corrupted binary sensor log file is located at `/app/data/sensorlog.dat`. It contains 300 sensor readings that were encoded into fixed-size binary frames and then corrupted with two transformations applied in sequence:

1. **Byte permutation**: Within each 64-byte frame, the bytes have been rearranged according to a fixed (unknown) permutation applied identically to every frame.
2. **XOR cipher**: After permutation, a repeating XOR key of length 64 bytes (same as frame size) is applied cyclically across the entire file. Since the key length equals the frame size, each byte position within a frame is XORed with the same key byte in every frame.

## Frame Format (before corruption)

Each original (uncorrupted) frame is exactly 64 bytes:

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0-3 | 4 | uint32 LE | Sequence number (0, 1, 2, ..., 299) |
| 4-15 | 12 | ASCII | Sensor name, null-padded (e.g., `temp-A1\x00\x00\x00\x00\x00`) |
| 16-39 | 24 | ASCII | Timestamp in ISO-8601 format, null-padded (e.g., `2024-03-15T08:30:00Z\x00\x00\x00\x00`) |
| 40-51 | 12 | ASCII | Sensor reading value as decimal text, null-padded (e.g., `784.0957\x00\x00\x00\x00`) |
| 52-63 | 12 | zero | Padding (all zero bytes) |

## Known Constraints

- Sequence numbers are sequential integers 0 through 299
- Sensor names follow the pattern `{type}-{letter}{digit}` where type is one of: `temp`, `pressure`, `humidity`, `flow`, `vibration`; letter is A-F; digit is 1-9. Sensor names are printable ASCII (bytes 0x20-0x7E) followed by null padding (0x00)
- Timestamps are valid UTC timestamps in March 2024, formatted as `2024-03-DDThh:mm:ssZ` where DD is 01-31, hh is 00-23, mm and ss are 00-59. Timestamps are printable ASCII followed by null padding
- Values are decimal numbers in the range 5.0 to 950.0, formatted with exactly 4 decimal places (e.g., "784.0957"). Values are printable ASCII (digits, '.') followed by null padding
- The padding region (bytes 52-63) is always all zeros in the original uncorrupted frames

## Your Task

Write a Python script at `/app/extract.py` that:

1. Reads `/app/data/sensorlog.dat`
2. Reverse-engineers the XOR key and byte permutation by analyzing patterns in the corrupted data (use the known structure: sequential IDs, ASCII-printable sensor/timestamp/value fields, zero padding, etc.)
3. Decodes all 300 frames
4. Outputs `/app/output/readings.json` as a JSON array of objects sorted by `seq`:

```json
[
  {"seq": 0, "sensor": "temp-A1", "timestamp": "2024-03-15T08:30:00Z", "value": 123.4567},
  ...
]
```

Each object must have:
- `seq`: integer sequence number
- `sensor`: string sensor name (no null padding)
- `timestamp`: string timestamp (no null padding)
- `value`: numeric reading value (float, rounded to 4 decimal places)

Create the output directory if it doesn't exist. The script should be runnable as `python /app/extract.py`.
