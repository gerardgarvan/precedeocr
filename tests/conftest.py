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
    """Sample pipeline results for CSV/JSON output testing (new multi-ID contract)."""
    return [
        {'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': '', 'folder_path': ''},
        {'filename': 'test.pdf', 'page': 2, 'ids': [], 'rotation_detected': None, 'notes': 'no_text_detected', 'folder_path': ''},
        {'filename': 'test.pdf', 'page': 3, 'ids': ['67890'], 'rotation_detected': 0, 'notes': '', 'folder_path': ''},
    ]


@pytest.fixture
def multi_id_results():
    """Sample results with multiple IDs on a single page."""
    return [
        {'filename': 'test.pdf', 'page': 1, 'ids': ['12345', '67890'], 'rotation_detected': 90, 'notes': '', 'folder_path': ''},
        {'filename': 'test.pdf', 'page': 2, 'ids': [], 'rotation_detected': None, 'notes': 'no_text_detected', 'folder_path': ''},
    ]
