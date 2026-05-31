"""Verification tests for sensor reading recovery."""
import hashlib, json, os

RS = 96
NR = 200
RECOVERED = '/app/recovered.bin'
REFERENCE = '/var/lib/tbench/.reference.json'

def load_ref():
    with open(REFERENCE) as f:
        return json.load(f)

def test_output_exists():
    """Output file must exist."""
    assert os.path.isfile(RECOVERED)

def test_output_size():
    """Output must be exactly 19200 bytes."""
    assert os.path.getsize(RECOVERED) == NR * RS

def test_full_hash():
    """SHA256 of full output must match reference."""
    ref = load_ref()
    with open(RECOVERED, 'rb') as f:
        h = hashlib.sha256(f.read()).hexdigest()
    assert h == ref['full_hash']

def test_individual_hashes():
    """Each reading must match its reference hash."""
    ref = load_ref()
    with open(RECOVERED, 'rb') as f:
        data = f.read()
    bad = [i for i in range(NR)
           if hashlib.sha256(data[i*RS:(i+1)*RS]).hexdigest() != ref['reading_hashes'][i]]
    assert len(bad) == 0, f"{len(bad)} readings wrong"

def test_padding():
    """Last block of every reading must be zero."""
    ref = load_ref()
    bs = ref['block_size']
    with open(RECOVERED, 'rb') as f:
        data = f.read()
    bad = [i for i in range(NR)
           if data[i*RS+RS-bs:(i+1)*RS] != b'\x00'*bs]
    assert len(bad) == 0

def test_header_linearity():
    """Header bytes must follow linear pattern mod 256."""
    ref = load_ref()
    bs = ref['block_size']
    with open(RECOVERED, 'rb') as f:
        data = f.read()
    for pos in range(bs):
        vals = [data[i*RS + pos] for i in range(NR)]
        O = vals[0]
        M = (vals[1] - O) % 256
        for idx in range(NR):
            assert vals[idx] == (idx * M + O) % 256
