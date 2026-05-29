A firmware image at `/app/data/firmware.bin` (64KB) contains a hidden configuration table that was encrypted before being embedded. We need to extract it.

Write `/app/extract.py` to find and decrypt the config, writing the result to `/app/output/config.json`.

What we know:
- The firmware has a header (first 256 bytes) with metadata including a 4-byte magic `0xFEEDFACE` at offset 0
- The header contains the encryption key and pointers to the config table
- Offsets and sizes in the header are 4-byte little-endian values
- The config table location (offset into the firmware) is stored at header byte 32
- The encrypted config size is stored at header byte 36
- The original (unpadded) config size is at header byte 40
- The decryption process involves three sequential transformations that must be reversed in opposite order
- The encryption details are NOT documented — you must figure them out by analyzing the binary data and known plaintext hints
- The plaintext config is JSON and starts with `{"device_id":"IOT-`
- The key material is 16 bytes located at header offset 16

Once decrypted, the config is a JSON object containing: `device_id`, `sensors` (array with `name`, `pin`, `calibration`), `network` (with `ssid`, `gateway`, `dns`), and `version`.

Output format: write the exact JSON content to `/app/output/config.json` without extra formatting.

Run: `python /app/extract.py`
