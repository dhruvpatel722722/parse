# Sensor Reading Recovery

The file `/app/readings.bin` (19200 bytes) contains 200 scrambled sensor readings of 96 bytes each.

Each reading was corrupted by two operations applied in sequence:
1. Within consecutive fixed-size blocks, byte positions were rearranged by a fixed shuffle pattern (the same unknown pattern for every block in every reading).
2. A repeating byte mask of unknown length was XORed across the shuffled result.

The original (unscrambled) reading format:
- **First block**: a calibration header where byte `i` equals `(reading_index * M[i] + O[i]) mod 256`. The multipliers M and offsets O are unknown but fixed; each position uses a distinct odd multiplier.
- **Middle blocks**: opaque sensor payload.
- **Last block**: all zero bytes (null padding).

Neither the block size, mask length, multipliers, nor offsets are provided. You must determine them by analyzing the data.

Write all 200 recovered plaintext readings sequentially to `/app/recovered.bin` (19200 bytes).
