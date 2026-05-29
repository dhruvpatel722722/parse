import os
import subprocess
import hashlib
import sys
import importlib


def test_compress_script_exists():
    """Test that the compression script was created at the expected path."""
    assert os.path.exists("/app/compress.py"), "compress.py does not exist"


def test_decompress_script_exists():
    """Test that the decompression script was created at the expected path."""
    assert os.path.exists("/app/decompress.py"), "decompress.py does not exist"


def test_compressed_file_exists():
    """Test that the compressed output file was produced."""
    assert os.path.exists("/app/output/compressed.bin"), "compressed.bin does not exist"


def test_restored_file_exists():
    """Test that the decompressed restored file was produced."""
    assert os.path.exists("/app/output/restored.bin"), "restored.bin does not exist"


def test_compression_ratio():
    """Test that the compression ratio exceeds 2.5x (compressed < 40% of original)."""
    orig_size = os.path.getsize("/app/data/corpus.bin")
    comp_size = os.path.getsize("/app/output/compressed.bin")
    ratio = orig_size / comp_size
    threshold = orig_size * 0.4
    assert comp_size < threshold, (
        f"Compressed size {comp_size} is not < 40% of original {orig_size} "
        f"(ratio: {ratio:.2f}x, need > 2.5x)"
    )


def test_lossless_decompression():
    """Test that decompression produces a byte-for-byte identical file to the original."""
    with open("/app/data/corpus.bin", "rb") as f:
        original = f.read()
    with open("/app/output/restored.bin", "rb") as f:
        restored = f.read()
    assert len(restored) == len(original), (
        f"Size mismatch: original {len(original)} vs restored {len(restored)}"
    )
    assert original == restored, "Decompressed file differs from original"


def test_decompression_hash_match():
    """Test that SHA-256 hash of restored file matches the original corpus."""
    def file_hash(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    
    orig_hash = file_hash("/app/data/corpus.bin")
    rest_hash = file_hash("/app/output/restored.bin")
    assert orig_hash == rest_hash, (
        f"Hash mismatch: original={orig_hash[:16]}... restored={rest_hash[:16]}..."
    )


def test_compress_runs_within_time_limit():
    """Test that the compression script completes within 30 seconds."""
    result = subprocess.run(
        [sys.executable, "/app/compress.py"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"compress.py failed: {result.stderr}"


def test_decompress_runs_within_time_limit():
    """Test that the decompression script completes within 30 seconds."""
    result = subprocess.run(
        [sys.executable, "/app/decompress.py"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"decompress.py failed: {result.stderr}"


def test_no_banned_imports_in_compress():
    """Test that compress.py does not use banned compression libraries."""
    with open("/app/compress.py", "r") as f:
        source = f.read()
    banned = ["zlib", "gzip", "lzma", "bz2", "snappy", "zstandard", "lz4", "brotli"]
    for lib in banned:
        assert lib not in source, f"Banned library '{lib}' found in compress.py"


def test_no_banned_imports_in_decompress():
    """Test that decompress.py does not use banned compression libraries."""
    with open("/app/decompress.py", "r") as f:
        source = f.read()
    banned = ["zlib", "gzip", "lzma", "bz2", "snappy", "zstandard", "lz4", "brotli"]
    for lib in banned:
        assert lib not in source, f"Banned library '{lib}' found in decompress.py"


def test_no_shell_compression_tools():
    """Test that scripts do not shell out to system compression utilities."""
    for script in ["/app/compress.py", "/app/decompress.py"]:
        with open(script, "r") as f:
            source = f.read()
        shell_tools = ["subprocess", "os.system", "os.popen", "Popen"]
        for tool in shell_tools:
            assert tool not in source, (
                f"Shell execution '{tool}' found in {script} - not allowed"
            )
