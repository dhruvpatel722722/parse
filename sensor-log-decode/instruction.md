A corrupted sensor log archive at `/app/data/sensorlog.dat` contains timestamped readings that were encoded by a faulty export module before being written to disk.

Write `/app/extract.py` to decode the archive and produce `/app/output/readings.json`.

Output format — a JSON array of objects sorted by `seq` ascending:
```
[{"seq": <int>, "sensor": "<string>", "timestamp": "<ISO-8601>", "value": <float>}, ...]
```

There are exactly 300 records with sequential `seq` values starting from 0.

What we know about the original record format:
- Records were serialized as fixed-width 64-byte frames
- Each frame: 4-byte LE sequence number, 16-byte null-padded sensor name, 24-byte null-padded ISO timestamp, 8-byte LE double (the reading value), 12 bytes padding
- Sensor names are like `temp-A1`, `pressure-B3`, `humidity-C2` etc.
- Timestamps are UTC in format `2024-MM-DDThh:mm:ssZ`
- Values are physically plausible (range 0-1000)

What we know about the encoding corruption:
- Two transformations were applied sequentially to the serialized byte stream
- The first transformation XORs each byte with a repeating key derived from the byte's position — the key length and values are unknown
- The second transformation shuffles bytes within fixed-size blocks using an unknown permutation
- Both transformations are deterministic and reversible
- The block size for the permutation is NOT 16 — you must determine it

You must reverse-engineer both transformations by analyzing patterns in the binary data, then decode all 300 records.

Run: `python /app/extract.py`
