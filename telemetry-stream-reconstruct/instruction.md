# Telemetry Stream Recovery

A satellite telemetry stream has been captured in `/app/telemetry.bin` (19200 bytes). The stream contains 300 frames of 64 bytes each that were obfuscated before transmission.

## Obfuscation Process

Each 64-byte frame was transformed by two operations applied in order:

1. **Block permutation**: A fixed (unknown) permutation of 16 bytes is applied independently to each 16-byte chunk within the frame. The operation is: `output[i] = input[perm[i]]` for each chunk.

2. **XOR masking**: A fixed (unknown) 32-byte key is XORed cyclically across the 64-byte permuted frame.

## Frame Structure (before obfuscation)

- **Bytes 0–15** (header): Each byte `i` is computed as `(seq * M[i] + O[i]) % 256` where `seq` is the frame sequence number (0–299), `M = [1,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53]`, and `O = [0,100,200,50,150,75,125,175,225,25,60,90,110,130,160,190]`.
- **Bytes 16–47**: Sensor payload (unknown random data).
- **Bytes 48–63**: Zero padding (16 null bytes).

## Task

Recover all 300 original plaintext frames and write them sequentially to `/app/recovered.bin` (19200 bytes total).
