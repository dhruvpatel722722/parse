"""Shared fixtures."""
import sys
import shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "environment"
FIXTURES = ENV / "fixtures"

sys.path.insert(0, str(ENV))

from src.wal_reader import WALReader


@pytest.fixture
def segments_dir():
    return FIXTURES / "segments"

@pytest.fixture
def fresh_segments_dir():
    return FIXTURES / "segments_fresh"

@pytest.fixture
def checkpoint_dir(tmp_path):
    """Copy checkpoint to temp so tests don't corrupt fixtures."""
    dst = tmp_path / "checkpoints"
    shutil.copytree(FIXTURES / "checkpoints", dst)
    return dst

@pytest.fixture
def tmp_output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    return d

@pytest.fixture
def tmp_checkpoint_dir(tmp_path):
    d = tmp_path / "cp_empty"
    d.mkdir()
    return d

@pytest.fixture
def loaded_segments(segments_dir):
    return WALReader(segments_dir).load_all_segments()

@pytest.fixture
def fresh_segments(fresh_segments_dir):
    return WALReader(fresh_segments_dir).load_all_segments()
