A corrupted log archive is at `/app/data/cipher_log.bin` (9600 bytes). It contains 150 encoded monitoring log entries.

Each original record is a 64-byte frame: 4-byte LE sequence ID (0-149), 8-byte null-padded category, 48-byte null-padded message, 4 bytes zero padding.

Write `/app/recover.py` to decode and output `/app/output/recovered.json` — a JSON array of objects with `id` (integer), `category` (string), `message` (string), sorted by `id`.

What is known about the corruption:

Two reversible transformations were applied to the raw byte stream:

- The first transformation rearranges bytes across record boundaries. It operates on fixed-size groups and redistributes bytes from multiple source records into combined output blocks.

- The second transformation modifies individual byte values using a circular bitwise operation. The operation is applied per fixed-size chunk and the shift parameter varies deterministically with chunk position in the stream.

The second transformation was applied after the first. To decode, reverse them in opposite order.

Categories are: auth, network, storage, compute, deploy, monitor, backup, sync, alert, config.

Messages follow format: `action target ts=NNNNNNNN id=HHHHHHHHHHHH` where action is a past-tense verb, target is a node/service name, ts is a numeric timestamp, and id is a 12-char hex string.

The bit operation chunk size divides evenly into the group size used by the first transformation. Both transformations preserve total byte count.

Run: `python /app/recover.py`
