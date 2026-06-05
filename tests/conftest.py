import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Provide a temporary directory, cleaned up after test."""
    d = tempfile.mkdtemp(prefix='precede_test_')
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_results():
    """Sample pipeline results for CSV output testing."""
    return [
        {'filename': 'test.pdf', 'page': 1, 'id': '12345', 'rotation_detected': 90},
        {'filename': 'test.pdf', 'page': 2, 'id': None, 'rotation_detected': None},
        {'filename': 'test.pdf', 'page': 3, 'id': '67890', 'rotation_detected': 0},
    ]
