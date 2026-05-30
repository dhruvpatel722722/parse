There's a corrupted database export at `/app/data/records.dat`. The file contains mangled records from a key-value store that went through some kind of encoding pipeline before being written to disk.

Your job is to write `/app/recover.py` that recovers the original data and writes it to `/app/output/recovered.json`.

The output must be a JSON array of objects with keys `id` (integer), `key` (string), `value` (string), sorted by `id` ascending. There are exactly 200 records with ids 0 through 199.

What we know about the original data format:
- Records were stored as fixed-width 128-byte frames (4-byte LE id, 32-byte null-padded key, 92-byte null-padded value)
- Keys follow the pattern `word.word.NNN` where words are from a fixed vocabulary and NNN is the zero-padded id
- Values contain structured text with fields like `data=`, `seq=`, and `hash=`

What we know about the corruption:
- Two transformations were applied sequentially to the serialized byte stream
- The first transformation operates on fixed-size blocks and shuffles byte positions within each block
- The second transformation XORs each byte with a value derived from its position
- Both transformations are deterministic and reversible

You must reverse-engineer both transformations by analyzing the binary patterns, then decode all 200 records. The vocabulary used for keys includes Greek letters and common tech terms.

Run: `python /app/recover.py`
