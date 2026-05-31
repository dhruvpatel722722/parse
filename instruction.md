# State Machine Telemetry Recovery

A telemetry recorder captured state transitions for 64 parallel channels into a binary log using a custom protocol. The file is at `/app/data/telemetry.bin`. A partial protocol description is in `/app/data/protocol.txt`.

## What you know

- Records are 19 bits each, packed in a continuous bitstream (not byte-aligned)
- Each record contains a channel ID, signed delta, and integrity check
- Records are XOR-scrambled with a rolling key that evolves after each record
- Some records (~15%) are corrupted and must be skipped
- Sync markers appear periodically and are not scrambled

## What you must discover

- The initial value of the XOR key
- The CRC-8 polynomial used for integrity checks
- How to distinguish valid records from corrupt ones

## Channel state tracking

Each channel starts at state 0. For each valid (non-corrupt) record, add the signed delta to that channel's state, wrapping modulo 256. The rolling key must be updated for ALL records (valid or corrupt) to maintain synchronization.

## Output

Write the final state of each channel (0 through 63) as decimal integers, one per line, to `/app/output/channel_states.txt` (64 lines total).
