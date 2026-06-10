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


@pytest.fixture
def sample_scan_csv(temp_dir):
    """Create a sample scan results CSV for lookup testing."""
    csv_path = Path(temp_dir) / "results.csv"
    csv_path.write_text(
        "filename,folder_path,page,id,rotation_detected,notes\n"
        "subdir1/fileA.pdf,subdir1,1,67890,90,\n"
        "subdir2/fileB.pdf,subdir2,1,12345,0,\n"
        "subdir1/fileA.pdf,subdir1,2,,None,no_text_detected\n"
        "subdir2/fileB.pdf,subdir2,2,99999,270,\n"
        "subdir1/fileA.pdf,subdir1,3,0,0,error: FileNotFoundError\n",
        encoding='utf-8'
    )
    return str(csv_path)
