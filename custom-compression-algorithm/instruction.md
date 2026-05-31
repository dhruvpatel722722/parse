# Custom Compression Algorithm Recovery

A binary database file at `/app/data/records.dat` contains 200 records that have been encoded with a custom compression/encryption scheme. Your task is to reverse-engineer the encoding and recover the original data.

## File Structure

The file is exactly **25,600 bytes** (200 frames × 128 bytes each).

Each original (plaintext) frame is 128 bytes with this layout:
- **Bytes 0–3**: Record ID as a 4-byte unsigned little-endian integer (IDs range from 0 to 199)
- **Bytes 4–35**: Key field, ASCII null-padded to 32 bytes
- **Bytes 36–127**: Value field, ASCII null-padded to 92 bytes

The frames are stored in order (frame 0 contains record ID 0, frame 1 contains ID 1, etc.).

## Transformations Applied

Two transformations were applied to each frame **in this order**:

1. **Block Shuffle**: Each 128-byte frame is divided into **16 blocks of 8 bytes** each. These blocks are then rearranged according to a fixed permutation. The same permutation is used for every frame. The permutation maps source block indices to destination positions — i.e., if `perm[dst] = src`, then block at destination position `dst` came from source position `src`.

2. **Positional XOR**: After shuffling, each byte of the 128-byte frame is XOR'd with a corresponding byte from a fixed 128-byte key. The same XOR key is used for every frame.

## Known Information for Recovery

Since you know the record IDs (0–199) and their positions, the first 4 bytes of each plaintext frame are **known** (the little-endian encoding of the ID). Additionally, the key and value fields are null-padded, meaning there are **zero bytes** at predictable positions in each plaintext frame. These known plaintext bytes, combined with the XOR'd output, allow you to determine the XOR key bytes at the corresponding shuffled positions. By comparing multiple frames with different known bytes, you can deduce the full permutation and XOR key.

## Output Format

Write a Python script at `/app/recover.py` that:
1. Reads `/app/data/records.dat`
2. Reverses the transformations to recover the original records
3. Outputs a JSON file at `/app/output/recovered.json`

The JSON should be an array of objects sorted by `id` ascending:
```json
[
  {"id": 0, "key": "word1.word2.123", "value": "data=abcdef0123456789, seq=12345, hash=deadbeef"},
  {"id": 1, "key": "word1.word2.456", "value": "data=..."},
  ...
]
```

Each object has three fields:
- `id`: integer (0–199)
- `key`: string in format `word.word.NNN` where words come from a vocabulary of Greek letters (alpha, beta, gamma, delta, epsilon, zeta, eta, theta, iota, kappa, lambda, mu, nu, xi, omicron, pi, rho, sigma, tau, upsilon, phi, chi, psi, omega) and tech terms (kernel, socket, buffer, cache, thread, mutex, queue, stack, heap, token, cipher, codec, proxy, router, bridge, driver, daemon, signal, packet, stream, vector, matrix, tensor, shader), and NNN is a 3-digit number (100–999)
- `value`: string in format `data=<16 hex chars>, seq=<integer>, hash=<8 hex chars>` where hash is the first 8 characters of SHA-256(data_hex + str(seq_num))

Make sure `/app/output/` exists before writing. Run the script after creating it.
