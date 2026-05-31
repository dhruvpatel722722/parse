"""
Verification tests for telemetry stream recovery.
Validates the recovered plaintext against reference hashes.
"""

import hashlib
import json
import os

FRAME_SIZE = 64
NUM_FRAMES = 300
RECOVERED_PATH = '/app/recovered.bin'
REFERENCE_PATH = '/var/lib/tbench/.reference.json'


def load_reference():
    """Load reference data for verification."""
    with open(REFERENCE_PATH, 'r') as f:
        return json.load(f)


def test_output_file_exists():
    """Recovered output file must exist at /app/recovered.bin."""
    assert os.path.isfile(RECOVERED_PATH), (
        f"Output file not found: {RECOVERED_PATH}"
    )


def test_output_file_size():
    """Recovered file must be exactly 19200 bytes (300 frames x 64 bytes)."""
    size = os.path.getsize(RECOVERED_PATH)
    expected = NUM_FRAMES * FRAME_SIZE
    assert size == expected, (
        f"File size {size} != expected {expected}"
    )


def test_full_plaintext_hash():
    """SHA256 of complete recovered plaintext must match reference."""
    ref = load_reference()
    with open(RECOVERED_PATH, 'rb') as f:
        data = f.read()
    h = hashlib.sha256(data).hexdigest()
    assert h == ref['full_plaintext_hash'], (
        f"Full hash mismatch: got {h[:16]}..."
    )


def test_individual_frame_hashes():
    """Each recovered frame must match its reference hash."""
    ref = load_reference()
    with open(RECOVERED_PATH, 'rb') as f:
        data = f.read()
    failures = []
    for i in range(NUM_FRAMES):
        frame = data[i*FRAME_SIZE:(i+1)*FRAME_SIZE]
        h = hashlib.sha256(frame).hexdigest()
        if h != ref['frame_hashes'][i]:
            failures.append(i)
    assert len(failures) == 0, (
        f"{len(failures)} frames incorrect, first: {failures[:5]}"
    )


def test_zero_padding_intact():
    """Bytes 48-63 of every frame must be zero padding."""
    with open(RECOVERED_PATH, 'rb') as f:
        data = f.read()
    failures = []
    for i in range(NUM_FRAMES):
        padding = data[i*FRAME_SIZE + 48:(i+1)*FRAME_SIZE]
        if padding != b'\x00' * 16:
            failures.append(i)
    assert len(failures) == 0, (
        f"{len(failures)} frames have non-zero padding"
    )


def test_header_consistency():
    """Header bytes must follow the documented linear formula."""
    multipliers = [1, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]
    offsets = [0, 100, 200, 50, 150, 75, 125, 175, 225, 25, 60, 90, 110, 130, 160, 190]
    with open(RECOVERED_PATH, 'rb') as f:
        data = f.read()
    failures = []
    for seq in range(NUM_FRAMES):
        header = data[seq*FRAME_SIZE:seq*FRAME_SIZE + 16]
        for i in range(16):
            expected = (seq * multipliers[i] + offsets[i]) % 256
            if header[i] != expected:
                failures.append((seq, i))
                break
    assert len(failures) == 0, (
        f"{len(failures)} frames have incorrect headers"
    )
