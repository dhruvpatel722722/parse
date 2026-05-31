A corrupted binary sensor log file is located at `/app/data/sensorlog.dat`. It contains 300 sensor readings that were encoded into fixed-size binary frames and then corrupted with two transformations applied in sequence:

1. **Byte permutation**: Within each 64-byte frame, the bytes have been rearranged according to a fixed (unknown) permutation applied identically to every frame.
2. **XOR cipher**: After permutation, a repeating XOR key of length 192 bytes (exactly 3 frames) is applied cyclically across the entire file.

## Frame Format (before corruption)

Each original (uncorrupted) frame is exactly 64 bytes:

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0-3 | 4 | uint32 LE | Sequence number (0, 1, 2, ..., 299) |
| 4-15 | 12 | ASCII | Sensor name, null-padded (e.g., `temp-A1\x00\x00\x00\x00\x00`) |
| 16-39 | 24 | ASCII | Timestamp in ISO-8601 format, null-padded (e.g., `2024-03-15T08:30:00Z\x00\x00\x00\x00`) |
| 40-47 | 8 | float64 LE | Sensor reading value |
| 48-63 | 16 | zero | Padding (all zero bytes) |

## Known Constraints

- Sequence numbers are sequential integers 0 through 299
- Sensor names follow the pattern `{type}-{letter}{digit}` where type is one of: `temp`, `pressure`, `humidity`, `flow`, `vibration`; letter is A-F; digit is 1-9. Sensor names are printable ASCII (bytes 0x20-0x7E) followed by null padding (0x00)
- Timestamps are valid UTC timestamps in March 2024, formatted as `2024-03-DDThh:mm:ssZ` where DD is 01-31, hh is 00-23, mm and ss are 00-59. Timestamps are printable ASCII followed by null padding
- Values are IEEE 754 double-precision floats in the range 5.0 to 950.0, rounded to 4 decimal places
- The padding region (bytes 48-63) is always all zeros in the original uncorrupted frames

## Cryptanalysis Hints

The following observations are key to recovering the original data:

1. **XOR-diff cancellation**: Since the XOR key repeats every 192 bytes (3 frames), frames that are exactly 3 apart share the same key bytes. XORing two frames at the same column position cancels the key: `corrupted[i][d] XOR corrupted[i+3][d] = permuted_orig[i][d] XOR permuted_orig[i+3][d]`. This reveals differences in the original data without knowing the key.

2. **Sequence number fingerprinting**: The sequence number at bytes 0-3 changes predictably (byte 0 = `i % 256`). By computing XOR-diffs between frames 3 apart at each column, you can identify which column holds sequence byte 0 — it will show diffs matching `(i%256) XOR ((i+3)%256)`. This uniquely identifies that column's permutation mapping.

3. **Constant-value columns**: Many source positions have identical values in every frame (zero padding bytes 48-63, timestamp prefix "2024-03-" at bytes 16-23, fixed characters 'T' at byte 26, ':' at bytes 29 and 32, 'Z' at byte 35). After permutation and XOR, these columns show zero XOR-diff between any two frames that share the same key cycle position (i.e., same `i % 3`). This identifies 32+ column-to-source mappings.

4. **Key recovery from known plaintext**: Once you know which column maps to which source position, and you know the original value (e.g., seq=0 means bytes 0-3 are all 0x00 in frame 0; padding is always 0x00), you can compute XOR key bytes directly: `key[(i*64 + d) % 192] = corrupted[i][d] XOR known_plaintext`.

5. **Full permutation via diff signatures**: Every source position (0-63) has a unique sequence of values across the 300 frames, producing a unique XOR-diff signature. Match each encrypted column's diff signature against the expected signatures for all possible source positions to determine the complete permutation.

## Your Task

Write a Python script at `/app/extract.py` that:

1. Reads `/app/data/sensorlog.dat`
2. Reverse-engineers the XOR key and byte permutation by analyzing patterns in the corrupted data
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
