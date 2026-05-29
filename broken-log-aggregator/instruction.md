There's a dataset at `/app/data/corpus.bin` (a binary file, roughly 1MB). You need to write a custom compressor and decompressor for it.

Create two scripts:
- `/app/compress.py` — reads `/app/data/corpus.bin`, writes compressed output to `/app/output/compressed.bin`
- `/app/decompress.py` — reads `/app/output/compressed.bin`, writes decompressed output to `/app/output/restored.bin`

Requirements:
1. The compressed file must be smaller than 40% of the original size (compression ratio > 2.5x)
2. Decompression must be perfectly lossless — the restored file must be byte-for-byte identical to the original
3. Both scripts must complete within 30 seconds each
4. You may NOT use any external compression libraries (no zlib, gzip, lzma, bz2, snappy, zstandard, etc.) — implement the algorithm yourself from scratch using only Python standard library (struct, collections, heapq, array, io, os, sys are fine)
5. You may NOT shell out to system compression tools

After creating both scripts, run them in sequence:
```
python /app/compress.py
python /app/decompress.py
```

Verify your output by comparing the files:
```
cmp /app/data/corpus.bin /app/output/restored.bin
```

The corpus contains structured English text with repeating patterns. Choose your compression strategy accordingly.
