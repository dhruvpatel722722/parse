#!/bin/bash
# Implement LZ77 + Huffman compression

cat > /app/compress.py << 'PYTHON'
import struct
import heapq
from collections import Counter
import os

def lz77_compress(data, window_size=8192, min_match=3, max_match=258):
    """LZ77 compression with hash-chain for fast matching."""
    tokens = []
    i = 0
    n = len(data)
    
    # Hash table: 3-byte hash -> list of positions
    from collections import defaultdict
    hash_chains = defaultdict(list)
    
    while i < n:
        best_offset = 0
        best_length = 0
        
        if i + 2 < n:
            # Hash of 3 bytes at current position
            h = (data[i] << 16) | (data[i+1] << 8) | data[i+2]
            
            # Search hash chain
            chain = hash_chains[h]
            for j in reversed(chain[-32:]):  # limit chain depth
                if i - j > window_size:
                    break
                # Extend match
                length = 0
                while (length < max_match and 
                       i + length < n and 
                       data[j + length] == data[i + length]):
                    length += 1
                
                if length > best_length:
                    best_length = length
                    best_offset = i - j
            
            chain.append(i)
        
        if best_length >= min_match:
            tokens.append((1, best_offset, best_length))
            # Add positions to hash for skipped bytes
            for k in range(1, best_length):
                if i + k + 2 < n:
                    hk = (data[i+k] << 16) | (data[i+k+1] << 8) | data[i+k+2]
                    hash_chains[hk].append(i + k)
            i += best_length
        else:
            tokens.append((0, data[i], 0))
            i += 1
    
    return tokens

def build_huffman_tree(freq):
    """Build Huffman tree from frequency dict, return code table."""
    if not freq:
        return {}
    if len(freq) == 1:
        symbol = list(freq.keys())[0]
        return {symbol: '0'}
    
    heap = [(count, i, symbol) for i, (symbol, count) in enumerate(freq.items())]
    heapq.heapify(heap)
    
    nodes = {}
    counter = len(heap)
    
    while len(heap) > 1:
        freq1, _, node1 = heapq.heappop(heap)
        freq2, _, node2 = heapq.heappop(heap)
        internal = ('internal', counter)
        counter += 1
        nodes[internal] = (node1, node2)
        heapq.heappush(heap, (freq1 + freq2, counter, internal))
        counter += 1
    
    if not heap:
        return {}
    
    root = heap[0][2]
    codes = {}
    
    def traverse(node, code):
        if node in nodes:
            left, right = nodes[node]
            traverse(left, code + '0')
            traverse(right, code + '1')
        else:
            codes[node] = code if code else '0'
    
    traverse(root, '')
    return codes

def compress():
    with open("/app/data/corpus.bin", "rb") as f:
        data = f.read()
    
    # LZ77 encode
    tokens = lz77_compress(data)
    
    # Collect symbols for Huffman
    # Literals: 0-255, Length codes: 256+length, Offset stored separately
    symbols = []
    offsets = []
    
    for token in tokens:
        if token[0] == 0:  # literal
            symbols.append(token[1])
        else:  # match
            symbols.append(256 + token[2])  # length as symbol
            offsets.append(token[1])
    
    # Huffman encode symbols
    freq = Counter(symbols)
    codes = build_huffman_tree(freq)
    
    # Encode to bits
    bits = []
    for sym in symbols:
        bits.append(codes[sym])
    bitstring = ''.join(bits)
    
    # Pack bits into bytes
    padding = (8 - len(bitstring) % 8) % 8
    bitstring += '0' * padding
    compressed_data = bytes(int(bitstring[i:i+8], 2) for i in range(0, len(bitstring), 8))
    
    # Encode offsets with simple variable-length encoding
    offset_bytes = bytearray()
    for off in offsets:
        if off < 128:
            offset_bytes.append(off)
        elif off < 16384:
            offset_bytes.append(0x80 | (off >> 8))
            offset_bytes.append(off & 0xFF)
        else:
            offset_bytes.append(0xC0 | (off >> 16))
            offset_bytes.append((off >> 8) & 0xFF)
            offset_bytes.append(off & 0xFF)
    
    # Write output
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/compressed.bin", "wb") as f:
        # Header
        f.write(struct.pack('<I', len(data)))  # original size
        f.write(struct.pack('<I', len(compressed_data)))  # huffman data size
        f.write(struct.pack('<I', len(offset_bytes)))  # offset data size
        f.write(struct.pack('<H', padding))  # bit padding
        f.write(struct.pack('<H', len(codes)))  # num symbols in codebook
        
        # Codebook
        for sym, code in sorted(codes.items()):
            f.write(struct.pack('<H', sym))  # symbol (2 bytes)
            f.write(struct.pack('<B', len(code)))  # code length
            # Pack code bits
            code_padded = code + '0' * ((8 - len(code) % 8) % 8)
            code_bytes = bytes(int(code_padded[i:i+8], 2) for i in range(0, len(code_padded), 8))
            f.write(struct.pack('<B', len(code_bytes)))
            f.write(code_bytes)
        
        # Data
        f.write(compressed_data)
        f.write(bytes(offset_bytes))
    
    orig_size = len(data)
    comp_size = os.path.getsize("/app/output/compressed.bin")
    ratio = orig_size / comp_size
    print(f"Original: {orig_size} bytes")
    print(f"Compressed: {comp_size} bytes")
    print(f"Ratio: {ratio:.2f}x")

if __name__ == "__main__":
    compress()
PYTHON

cat > /app/decompress.py << 'PYTHON'
import struct
import os

def decompress():
    with open("/app/output/compressed.bin", "rb") as f:
        # Read header
        orig_size = struct.unpack('<I', f.read(4))[0]
        huff_data_size = struct.unpack('<I', f.read(4))[0]
        offset_data_size = struct.unpack('<I', f.read(4))[0]
        padding = struct.unpack('<H', f.read(2))[0]
        num_symbols = struct.unpack('<H', f.read(2))[0]
        
        # Read codebook
        codes = {}
        for _ in range(num_symbols):
            sym = struct.unpack('<H', f.read(2))[0]
            code_len = struct.unpack('<B', f.read(1))[0]
            num_code_bytes = struct.unpack('<B', f.read(1))[0]
            code_bytes = f.read(num_code_bytes)
            # Extract code bits
            bits = ''.join(f'{b:08b}' for b in code_bytes)[:code_len]
            codes[bits] = sym
        
        # Read compressed data
        huff_data = f.read(huff_data_size)
        offset_data = f.read(offset_data_size)
    
    # Decode Huffman
    bitstring = ''.join(f'{b:08b}' for b in huff_data)
    if padding > 0:
        bitstring = bitstring[:-padding]
    
    symbols = []
    current = ''
    for bit in bitstring:
        current += bit
        if current in codes:
            symbols.append(codes[current])
            current = ''
    
    # Decode offsets
    offsets = []
    oi = 0
    while oi < len(offset_data):
        b = offset_data[oi]
        if b < 0x80:
            offsets.append(b)
            oi += 1
        elif b < 0xC0:
            off = ((b & 0x3F) << 8) | offset_data[oi + 1]
            offsets.append(off)
            oi += 2
        else:
            off = ((b & 0x3F) << 16) | (offset_data[oi + 1] << 8) | offset_data[oi + 2]
            offsets.append(off)
            oi += 3
    
    # Reconstruct data
    output = bytearray()
    offset_idx = 0
    
    for sym in symbols:
        if sym < 256:  # literal
            output.append(sym)
        else:  # match reference
            length = sym - 256
            offset = offsets[offset_idx]
            offset_idx += 1
            start = len(output) - offset
            for k in range(length):
                output.append(output[start + k])
    
    # Trim to original size
    output = output[:orig_size]
    
    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/restored.bin", "wb") as f:
        f.write(output)
    
    print(f"Decompressed: {len(output)} bytes")

if __name__ == "__main__":
    decompress()
PYTHON

# Run compression
python /app/compress.py

# Run decompression
python /app/decompress.py

# Verify
if cmp -s /app/data/corpus.bin /app/output/restored.bin; then
    echo "Verification: PASSED (files are identical)"
else
    echo "Verification: FAILED"
fi
