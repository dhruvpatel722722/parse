# Sensor Reading Recovery

The file `/app/readings.bin` (19200 bytes) contains 200 scrambled sensor readings of 96 bytes each.

Each reading was corrupted by two operations applied in sequence:
1. Within consecutive fixed-size blocks, byte positions were rearranged by a fixed shuffle (the same unknown pattern for every block in every reading).
2. A repeating byte mask was XORed across the shuffled result.

The original (unscrambled) reading format:
- **First block**: a calibration header where byte position `i` follows `(reading_index * M[i] + O[i]) mod 256` with known multipliers `M = [23, 1, 41, 7, 31, 11, 3, 37, 29, 13, 19, 17]` and unknown offsets O.
- **Middle blocks**: opaque sensor payload.
- **Last block**: all zero bytes (null padding).

The block size and mask length are not provided and must be determined from the data.

Write all 200 recovered plaintext readings sequentially to `/app/recovered.bin` (19200 bytes).
