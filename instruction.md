A corrupted packet log is at `/app/data/packets.bin` (25600 bytes). It contains 200 encoded network monitoring entries that went through an encoding pipeline before being written to disk.

Write `/app/recover.py` to decode and output `/app/output/recovered.json` — a JSON array of objects with `id` (integer), `source` (string), `payload` (string), sorted by `id`.

Each original record is a fixed 128-byte frame: 4-byte LE sequence ID (0-199), 32-byte null-padded source string, 88-byte null-padded payload string, and 4 bytes of zero padding at frame end.

What is known about the corruption:

Two deterministic reversible transformations were applied sequentially:

1. A fixed byte-position shuffle operates on equal-sized blocks throughout the stream. The same reordering is applied to every block. The block size is a power of two but smaller than the frame size.

2. A repeating XOR mask is applied across the entire byte stream. The mask length does not equal the block size.

The shuffle was applied first, then the XOR mask.

Source strings follow pattern `protocol.status.hexhash`. Payload strings follow `ts=NNNNNNNNNNNN len=NNNNN sig=HHHHHHHHHHHHHHHHHHHHHHHH`.

The sequential IDs (0-199 as 4-byte LE) and the trailing zero-padding provide known plaintext. XOR-difference between frames at the same block offset cancels the mask, exposing relationships between the permuted original bytes — enabling recovery of both the shuffle pattern and the XOR mask.

Run: `python /app/recover.py`
