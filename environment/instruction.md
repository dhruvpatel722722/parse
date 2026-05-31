# Sensor Reading Recovery

The file `/app/readings.bin` (19200 bytes) contains 200 scrambled sensor readings of 96 bytes each.

Each reading was corrupted by two operations applied in sequence:
1. Within consecutive fixed-size blocks, byte positions were rearranged by a fixed shuffle (the same unknown pattern for every block in every reading).
2. A repeating byte mask was XORed across the shuffled result.

The original (unscrambled) reading format:
- **First block**: a calibration header. Each header byte `i` follows `(reading_index * M[i] + O[i]) mod 256` with unknown multipliers M and known offsets `O = [175, 0, 60, 100, 225, 150, 50, 10, 200, 25, 75, 125]`. Each multiplier is a distinct odd number in [1, 255].
- **Middle blocks**: opaque sensor payload.
- **Last block**: all zero bytes (null padding).

The block size and mask length are not provided and must be determined from the data.

Write all 200 recovered plaintext readings sequentially to `/app/recovered.bin` (19200 bytes).
