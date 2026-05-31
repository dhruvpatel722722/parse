# Scrambled Record Recovery

A data file `/app/data.bin` (19200 bytes) contains 200 records of 96 bytes each that were scrambled by a two-layer process:

1. A fixed byte-position shuffle applied independently to consecutive fixed-size blocks within each record.
2. A fixed repeating mask XORed across the shuffled result.

Each original record had:
- A calibration header occupying the first block, where byte `i` follows `(record_index * M[i] + O[i]) mod 256` with multipliers `M = [23, 1, 41, 7, 31, 11, 3, 37, 29, 13, 19, 17]` and unknown offsets O.
- 12 null bytes (`0x00`) at the end (occupying the last block).

Note: the mask repeats with a period that is a multiple of the block size but not necessarily equal to it. Both the block size and the mask period must be determined from the data.

Recover all 200 original records in order and write them to `/app/recovered.bin` (19200 bytes).
