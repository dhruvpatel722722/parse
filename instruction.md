A corrupted sensor log at `/app/data/sensorlog.dat` contains 300 timestamped readings that were mangled by a buggy export pipeline before being written to disk.

Write `/app/extract.py` to recover the data and produce `/app/output/readings.json`.

Output: JSON array of objects sorted by `seq`:
```
[{"seq": <int>, "sensor": "<name>", "timestamp": "<ISO-8601>", "value": <float>}, ...]
```

About the original data:
- 300 records with `seq` values 0 through 299
- Each serialized as a 64-byte frame: 4-byte LE seq, 16-byte null-padded sensor name, 24-byte null-padded timestamp, 8-byte LE double value, 12 bytes padding (zeros)
- Sensor names match pattern like `temp-A1`, `pressure-B3`, `flow-E2`
- Timestamps are `2024-03-DDThh:mm:ssZ`
- Values range 5 to 950

About the corruption:
- Two byte-level transformations were applied sequentially to the raw serialized stream
- One transformation is a repeating XOR cipher — the key length and content are unknown
- The other transformation rearranges bytes within fixed-size blocks — both the block size and permutation are unknown
- The order in which the transformations were applied is unknown
- Neither transformation's parameters are stored anywhere in the file

You must analyze byte patterns to determine all unknown parameters (key, block size, permutation, and transformation order), then reverse both to recover the original records.

Run: `python /app/extract.py`
