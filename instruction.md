A corrupted telemetry archive is at `/app/data/telemetry.bin` (22750 bytes). It contains 250 encoded sensor records from a distributed monitoring cluster.

Each original record is a fixed 91-byte frame: 4-byte LE sequence ID (0-249), 40-byte null-padded field1, 44-byte null-padded field2, and 3 bytes of zero padding.

Write `/app/recover.py` to decode and output `/app/output/recovered.json` — a JSON array of objects with `id` (integer), `field1` (string), `field2` (string), sorted by `id`.

What is known about the corruption:

Two deterministic reversible transformations were applied to the raw byte stream. One shuffles byte positions within fixed-size blocks. The other applies a repeating byte mask across the stream. The block size and mask length are both unknown and are not equal to each other or to the frame size. All three values are mutually coprime.

The transformations interact: because the mask period and block size share no common factor with the frame size, the byte-level alignment shifts from frame to frame. Only frames separated by a specific interval share identical alignment — discovering that interval is essential.

Field1 values follow `nodename.channel.hexhash` format. Field2 values follow `val=NNNN.NN ts=NNNNNNNNNN chk=HHHHHHHHHHHH` format.

The sequential IDs and trailing zero-padding provide known plaintext at fixed positions within each frame. These anchors, combined with alignment-matched frame pairs, enable systematic recovery of both transformations.

Run: `python /app/recover.py`
