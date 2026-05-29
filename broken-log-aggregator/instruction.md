There's a scrambled database dump at `/app/data/records.dat`. It was exported from a key-value store but something went wrong during the export — the records are mangled.

Your job is to write a recovery script at `/app/recover.py` that:
1. Reads `/app/data/records.dat`
2. Figures out how the data was scrambled
3. Recovers the original records
4. Writes the recovered data to `/app/output/recovered.json`

The output must be a JSON array of objects, each with keys `id` (integer), `key` (string), and `value` (string), sorted by `id` ascending.

Hints about the corruption:
- The original records were serialized as fixed-width binary frames (each frame is exactly 128 bytes)
- Each frame contains: 4-byte little-endian id, 32-byte null-padded key, 92-byte null-padded value
- After serialization, a byte-level transformation was applied to the entire file
- The transformation operates on 16-byte blocks independently
- Within each block, bytes were permuted (reordered) using a fixed permutation pattern
- The permutation pattern repeats every 16 bytes throughout the file
- There are exactly 200 records in the original dataset

Your script must determine the permutation, reverse it, then parse the frames. Write the result as JSON to `/app/output/recovered.json`.

Run your script after creating it: `python /app/recover.py`
