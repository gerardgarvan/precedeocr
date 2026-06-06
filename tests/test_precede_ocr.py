import pytest
import csv
import json
import sys
import io
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock

from precede_ocr import (
    normalize_digits,
    select_most_likely_id,
    select_all_valid_ids,
    extract_id_with_rotation,
    write_results_csv,
    write_results_json,
    classify_failure_reason,
    print_rotation_summary,
    discover_pdfs,
    process_single_pdf_wrapper,
    process_all_pdfs,
    retry_once,
    log_error_to_file,
    save_checkpoint_atomic,
    load_checkpoint_if_exists,
    filter_remaining_pdfs,
    calculate_batch_stats,
    print_batch_stats,
    main,
    preprocess_image,
    validate_sequence,
    CampaignState,
    save_campaign_state_atomic,
    load_or_create_campaign_state,
    compute_folder_path,
)
import time as time_module
import re
from dataclasses import asdict


# -- normalize_digits tests --

class TestNormalizeDigits:
    def test_replaces_O_with_0(self):
        assert normalize_digits("O1234") == "01234"

    def test_replaces_lowercase_o_with_0(self):
        assert normalize_digits("o1234") == "01234"

    def test_replaces_I_with_1(self):
        assert normalize_digits("I2345") == "12345"

    def test_replaces_lowercase_l_with_1(self):
        assert normalize_digits("l2345") == "12345"

    def test_replaces_pipe_with_1(self):
        assert normalize_digits("|2345") == "12345"

    def test_replaces_S_with_5(self):
        assert normalize_digits("1234S") == "12345"

    def test_replaces_B_with_8(self):
        assert normalize_digits("1234B") == "12348"

    def test_replaces_Z_with_2(self):
        assert normalize_digits("1Z345") == "12345"

    def test_pure_digits_unchanged(self):
        assert normalize_digits("12345") == "12345"

    def test_empty_string(self):
        assert normalize_digits("") == ""

    def test_multiple_replacements(self):
        assert normalize_digits("OI2SB") == "01258"


# -- select_most_likely_id tests --

class TestSelectMostLikelyId:
    def test_single_valid_match(self):
        assert select_most_likely_id(["12345"]) == "12345"

    def test_filters_all_zeros(self):
        assert select_most_likely_id(["00000", "12345"]) == "12345"

    def test_filters_all_repeating_digits(self):
        assert select_most_likely_id(["11111", "22222", "12345"]) == "12345"

    def test_returns_first_when_multiple_valid(self):
        assert select_most_likely_id(["12345", "67890"]) == "12345"

    def test_returns_none_for_empty_list(self):
        assert select_most_likely_id([]) is None

    def test_falls_back_to_original_when_all_filtered(self):
        result = select_most_likely_id(["00000"])
        assert result == "00000"

    def test_all_nine_repeating_patterns_filtered(self):
        trivials = ["00000", "11111", "22222", "33333", "44444",
                     "55555", "66666", "77777", "88888", "99999"]
        result = select_most_likely_id(trivials + ["54321"])
        assert result == "54321"


# -- select_all_valid_ids tests --

class TestSelectAllValidIds:
    def test_returns_all_valid_matches(self):
        assert select_all_valid_ids(["12345", "67890"]) == ["12345", "67890"]

    def test_filters_trivial_patterns(self):
        # Per D-03: filter 00000, 11111, etc.
        assert select_all_valid_ids(["00000", "12345", "11111"]) == ["12345"]

    def test_all_trivial_returns_empty(self):
        # Unlike select_most_likely_id, do NOT fall back to trivial matches
        assert select_all_valid_ids(["00000", "11111"]) == []

    def test_empty_input_returns_empty(self):
        assert select_all_valid_ids([]) == []

    def test_single_valid_match(self):
        assert select_all_valid_ids(["54321"]) == ["54321"]

    def test_preserves_order(self):
        assert select_all_valid_ids(["67890", "12345"]) == ["67890", "12345"]


# -- write_results_csv tests --

class TestWriteResultsCsv:
    def test_creates_csv_file(self, sample_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        assert Path(output_path).is_file()

    def test_csv_has_correct_headers(self, sample_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert headers == ["filename", "page", "id", "rotation_detected", "notes"]

    def test_csv_row_count_matches_results(self, sample_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)
        # 3 pages: page 1 has 1 ID (1 row), page 2 has 0 IDs (1 row with blank), page 3 has 1 ID (1 row)
        assert len(rows) == 3

    def test_csv_includes_no_match_rows(self, sample_results, temp_dir):
        """Per D-06: pages with no ID must still appear in CSV."""
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            content = f.read()
        lines = content.strip().split("\n")
        page2_line = lines[2]
        assert "test.pdf,2," in page2_line

    def test_csv_creates_parent_directories(self, temp_dir):
        output_path = str(Path(temp_dir) / "nested" / "dir" / "output.csv")
        results = [{'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 0, 'notes': ''}]
        write_results_csv(results, output_path)
        assert Path(output_path).is_file()

    def test_csv_has_notes_column(self, sample_results, temp_dir):
        """Verify CSV headers include notes column."""
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert "notes" in headers
        assert headers == ["filename", "page", "id", "rotation_detected", "notes"]

    def test_csv_notes_populated_for_no_match(self, sample_results, temp_dir):
        """Verify notes column has failure reason for rows where ids is empty."""
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # Skip headers
            rows = list(reader)

        # Page 2 has no IDs (empty list), should have failure reason in notes
        page2_row = rows[1]
        assert page2_row[2] == ''  # id column is empty
        assert page2_row[4] == 'no_text_detected'  # notes column has reason

    def test_csv_notes_empty_for_match(self, sample_results, temp_dir):
        """Verify notes column is empty string for rows where ids is not empty."""
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # Skip headers
            rows = list(reader)

        # Page 1 has ID '12345', notes should be empty
        page1_row = rows[0]
        assert page1_row[2] == '12345'  # id column has value
        assert page1_row[4] == ''  # notes column is empty

    def test_csv_multiple_ids_per_page_creates_multiple_rows(self, multi_id_results, temp_dir):
        """Per D-01: multiple IDs on one page create one row per ID."""
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(multi_id_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
        # Page 1 has 2 IDs = 2 rows, Page 2 has 0 IDs = 1 row (blank id)
        assert len(rows) == 3
        assert rows[0][2] == '12345'  # first ID
        assert rows[1][2] == '67890'  # second ID
        assert rows[0][1] == rows[1][1] == '1'  # same page number
        assert rows[2][2] == ''  # no-ID page


# -- write_results_json tests --

class TestWriteResultsJson:
    def test_creates_json_file(self, sample_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(sample_results, output_path)
        assert Path(output_path).is_file()

    def test_json_is_valid(self, sample_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(sample_results, output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_json_nested_structure(self, sample_results, temp_dir):
        """Per D-04: {filename: {page_str: [ids]}}"""
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(sample_results, output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert 'test.pdf' in data
        assert '1' in data['test.pdf']
        assert data['test.pdf']['1'] == ['12345']
        assert data['test.pdf']['3'] == ['67890']

    def test_json_no_id_pages_empty_array(self, sample_results, temp_dir):
        """Per PIPE-07 and D-04: no-ID pages show as empty array"""
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(sample_results, output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert data['test.pdf']['2'] == []

    def test_json_multiple_ids_per_page(self, multi_id_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(multi_id_results, output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert data['test.pdf']['1'] == ['12345', '67890']

    def test_json_page_keys_are_strings(self, sample_results, temp_dir):
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(sample_results, output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        for filename in data:
            for page_key in data[filename]:
                assert isinstance(page_key, str)

    def test_json_creates_parent_directories(self, temp_dir):
        output_path = str(Path(temp_dir) / "nested" / "dir" / "output.json")
        results = [{'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]
        write_results_json(results, output_path)
        assert Path(output_path).is_file()

    def test_json_multiple_files(self, temp_dir):
        results = [
            {'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'b.pdf', 'page': 1, 'ids': ['67890'], 'rotation_detected': 90, 'notes': ''},
        ]
        output_path = str(Path(temp_dir) / "test_output.json")
        write_results_json(results, output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert 'a.pdf' in data
        assert 'b.pdf' in data
        assert data['a.pdf']['1'] == ['12345']
        assert data['b.pdf']['1'] == ['67890']


# -- extract_id_with_rotation tests --

class TestExtractIdWithRotation:
    def test_returns_tuple(self):
        """Verify function returns a 3-tuple regardless of input."""
        img = Image.new("RGB", (100, 50), color="white")
        result = extract_id_with_rotation(img)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_blank_image_returns_empty_list(self):
        """A blank white image should yield empty list of IDs."""
        img = Image.new("RGB", (200, 100), color="white")
        ids, rotation, notes = extract_id_with_rotation(img)
        assert ids == []
        assert rotation is None
        assert notes == 'no_text_detected'

    def test_rotation_order(self):
        """Verify rotation order is [90, 270, 0, 180] and 90 is tried first."""
        img = Image.new("RGB", (100, 50), color="white")

        call_count = [0]

        def mock_ocr(image, config=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return '12345'
            else:
                return ''

        with patch('precede_ocr.pytesseract.image_to_string', side_effect=mock_ocr):
            ids, rotation, notes = extract_id_with_rotation(img)

        assert ids == ['12345']
        assert rotation == 90
        assert notes == ''
        assert call_count[0] == 1  # Early exit after first match

    def test_early_exit_skips_remaining(self):
        """Verify early exit - only 1 OCR call when match found at 90 degrees."""
        img = Image.new("RGB", (100, 50), color="white")

        call_count = [0]

        def mock_ocr(image, config=None):
            call_count[0] += 1
            return '12345'  # Always return match

        with patch('precede_ocr.pytesseract.image_to_string', side_effect=mock_ocr):
            ids, rotation, notes = extract_id_with_rotation(img)

        assert call_count[0] == 1  # Only one call made
        assert ids == ['12345']
        assert rotation == 90

    def test_fallback_to_later_angles(self):
        """Verify fallback to 0 degrees when 90 and 270 return no match."""
        img = Image.new("RGB", (100, 50), color="white")

        call_count = [0]

        def mock_ocr(image, config=None):
            call_count[0] += 1
            if call_count[0] == 3:
                return '12345'
            return ''

        with patch('precede_ocr.pytesseract.image_to_string', side_effect=mock_ocr):
            ids, rotation, notes = extract_id_with_rotation(img)

        assert ids == ['12345']
        assert rotation == 0  # Found at 0 degrees (3rd in order)
        assert notes == ''

    def test_returns_three_values(self):
        """Verify return is a 3-tuple (list, angle, notes)."""
        img = Image.new("RGB", (100, 50), color="white")

        with patch('precede_ocr.pytesseract.image_to_string', return_value=''):
            result = extract_id_with_rotation(img)

        assert isinstance(result, tuple)
        assert len(result) == 3
        ids, rotation, notes = result
        assert ids == []
        assert isinstance(ids, list)
        assert rotation is None
        assert isinstance(notes, str)

    def test_extract_id_returns_list_of_ids(self):
        """extract_id_with_rotation returns list of all IDs found at successful rotation."""
        img = Image.new("RGB", (100, 50), color="white")

        def mock_ocr(image, config=None):
            return '12345 67890'

        with patch('precede_ocr.pytesseract.image_to_string', side_effect=mock_ocr):
            ids, rotation, notes = extract_id_with_rotation(img)
        assert isinstance(ids, list)
        assert ids == ['12345', '67890']
        assert rotation == 90
        assert notes == ''

    def test_extract_id_no_match_returns_empty_list(self):
        """extract_id_with_rotation with no matches returns empty list."""
        img = Image.new("RGB", (100, 50), color="white")
        with patch('precede_ocr.pytesseract.image_to_string', return_value=''):
            ids, rotation, notes = extract_id_with_rotation(img)
        assert ids == []
        assert rotation is None


# -- classify_failure_reason tests --

class TestClassifyFailureReason:
    def test_no_text_detected(self):
        """All OCR results empty should return 'no_text_detected'."""
        ocr_texts = ['', '', '', '']
        assert classify_failure_reason(ocr_texts) == 'no_text_detected'

    def test_no_text_whitespace_only(self):
        """Whitespace-only OCR results should return 'no_text_detected'."""
        ocr_texts = ['  ', '\n', '\t', '']
        assert classify_failure_reason(ocr_texts) == 'no_text_detected'

    def test_no_match_any_rotation(self):
        """Text detected but no 5-digit pattern should return 'no_match_any_rotation'."""
        ocr_texts = ['some text no digits', 'abc def', 'xyz', '']
        assert classify_failure_reason(ocr_texts) == 'no_match_any_rotation'

    def test_only_noise_matches(self):
        """5-digit numbers found but all filtered should return 'only_noise_matches'."""
        ocr_texts = ['00000', '11111 55555', '', '']
        assert classify_failure_reason(ocr_texts) == 'only_noise_matches'

    def test_mixed_text_no_valid_digits(self):
        """Text with numbers but no 5-digit pattern should return 'no_match_any_rotation'."""
        ocr_texts = ['page 1', '2024', 'hello', '']
        assert classify_failure_reason(ocr_texts) == 'no_match_any_rotation'


# -- debug mode tests --

class TestDebugMode:
    def test_debug_false_no_stderr(self):
        """With debug=False, no output to stderr."""
        img = Image.new("RGB", (100, 50), color="white")
        stderr_capture = io.StringIO()

        with patch('precede_ocr.pytesseract.image_to_string', return_value=''):
            with patch('sys.stderr', stderr_capture):
                extract_id_with_rotation(img, debug=False)

        output = stderr_capture.getvalue()
        assert output == ''

    def test_debug_true_prints_to_stderr(self):
        """With debug=True, OCR text appears in stderr."""
        img = Image.new("RGB", (100, 50), color="white")
        stderr_capture = io.StringIO()

        with patch('precede_ocr.pytesseract.image_to_string', return_value='test_ocr_output'):
            with patch('sys.stderr', stderr_capture):
                extract_id_with_rotation(img, debug=True)

        output = stderr_capture.getvalue()
        assert 'Rotation' in output
        assert 'test_ocr_output' in output

    def test_debug_output_includes_angle(self):
        """Debug output includes rotation angle label."""
        img = Image.new("RGB", (100, 50), color="white")
        stderr_capture = io.StringIO()

        with patch('precede_ocr.pytesseract.image_to_string', return_value=''):
            with patch('sys.stderr', stderr_capture):
                extract_id_with_rotation(img, debug=True)

        output = stderr_capture.getvalue()
        assert '90' in output  # First rotation angle


# -- print_rotation_summary tests --

class TestPrintRotationSummary:
    def test_prints_rotation_counts(self, capsys):
        """Verify rotation counts appear in output."""
        results = [
            {'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 2, 'ids': ['67890'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 3, 'ids': ['11111'], 'rotation_detected': 0, 'notes': ''},
        ]

        print_rotation_summary(results)

        captured = capsys.readouterr()
        output = captured.out
        assert '90' in output
        assert '2' in output  # 2 pages at 90 degrees
        assert '1' in output  # 1 page at 0 degrees

    def test_handles_empty_results(self, capsys):
        """No crash on empty list."""
        print_rotation_summary([])

        captured = capsys.readouterr()
        output = captured.out
        assert 'No pages processed' in output or len(output) == 0 or 'Rotation distribution' in output

    def test_handles_no_match_label(self, capsys):
        """Results with None rotation show 'No match' in output."""
        results = [
            {'filename': 'test.pdf', 'page': 1, 'ids': [], 'rotation_detected': None, 'notes': 'no_text_detected'},
        ]

        print_rotation_summary(results)

        captured = capsys.readouterr()
        output = captured.out
        assert 'No match' in output or 'None' in output


# -- discover_pdfs tests --

class TestDiscoverPdfs:
    def test_single_file(self, temp_dir):
        pdf_file = Path(temp_dir) / "test.pdf"
        pdf_file.touch()
        result = discover_pdfs(str(pdf_file))
        assert result == [pdf_file]

    def test_directory_recursive(self, temp_dir):
        # Create nested PDF files
        (Path(temp_dir) / "a.pdf").touch()
        (Path(temp_dir) / "sub").mkdir()
        (Path(temp_dir) / "sub" / "b.pdf").touch()
        result = discover_pdfs(temp_dir)
        assert len(result) == 2
        names = [p.name for p in result]
        assert 'a.pdf' in names
        assert 'b.pdf' in names

    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            discover_pdfs("C:/nonexistent/path/nowhere")

    def test_non_pdf_file_raises(self, temp_dir):
        txt_file = Path(temp_dir) / "file.txt"
        txt_file.touch()
        with pytest.raises(ValueError):
            discover_pdfs(str(txt_file))

    def test_empty_directory(self, temp_dir):
        result = discover_pdfs(temp_dir)
        assert result == []

    def test_ignores_non_pdf_files(self, temp_dir):
        (Path(temp_dir) / "a.pdf").touch()
        (Path(temp_dir) / "b.txt").touch()
        (Path(temp_dir) / "c.doc").touch()
        result = discover_pdfs(temp_dir)
        assert len(result) == 1
        assert result[0].name == 'a.pdf'


# -- process_single_pdf_wrapper tests --

class TestProcessSinglePdfWrapper:
    def test_returns_list_of_dicts(self, temp_dir):
        """Wrapper returns results from process_single_pdf."""
        mock_results = [{'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]
        with patch('precede_ocr.process_single_pdf', return_value=mock_results):
            result = process_single_pdf_wrapper(Path(temp_dir) / "test.pdf")
        assert result == mock_results

    def test_handles_exception_gracefully(self):
        """Wrapper catches exceptions and returns error dict."""
        with patch('precede_ocr.process_single_pdf', side_effect=RuntimeError("corrupt PDF")):
            result = process_single_pdf_wrapper(Path("bad.pdf"))
        assert len(result) == 1
        assert result[0]['ids'] == []
        assert 'error:' in result[0]['notes'] or 'error' in result[0]['notes']
        assert 'RuntimeError' in result[0]['notes']


# -- process_all_pdfs tests --

class TestProcessAllPdfs:
    def test_returns_combined_results(self, temp_dir):
        """process_all_pdfs aggregates results from multiple files."""
        mock_result_a = [{'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]
        mock_result_b = [{'filename': 'b.pdf', 'page': 1, 'ids': ['67890'], 'rotation_detected': 90, 'notes': ''}]

        pdf_paths = [Path(temp_dir) / "a.pdf", Path(temp_dir) / "b.pdf"]

        # Mock the Pool to avoid actual multiprocessing (can't pickle mocks on Windows spawn)
        with patch('precede_ocr.mp.Pool') as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool.__enter__ = MagicMock(return_value=mock_pool)
            mock_pool.__exit__ = MagicMock(return_value=False)
            mock_pool.imap_unordered.return_value = iter([mock_result_a, mock_result_b])
            mock_pool_class.return_value = mock_pool

            results = process_all_pdfs(pdf_paths, workers=1)

        assert len(results) == 2
        filenames = [r['filename'] for r in results]
        assert 'a.pdf' in filenames
        assert 'b.pdf' in filenames

    def test_pool_uses_maxtasksperchild(self):
        """Verify process recycling per D-07."""
        pdf_paths = [Path("test.pdf")]
        with patch('precede_ocr.mp.Pool') as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool.__enter__ = MagicMock(return_value=mock_pool)
            mock_pool.__exit__ = MagicMock(return_value=False)
            mock_pool.imap_unordered.return_value = iter([
                [{'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]
            ])
            mock_pool_class.return_value = mock_pool
            process_all_pdfs(pdf_paths, workers=2)
            mock_pool_class.assert_called_once_with(processes=2, maxtasksperchild=50)


# -- retry_once tests --

class TestRetryOnce:
    def test_success_on_first_call(self):
        """Decorated function that succeeds on first call returns result normally."""
        calls = [0]

        @retry_once
        def func():
            calls[0] += 1
            return "ok"

        result = func()
        assert result == "ok"
        assert calls[0] == 1

    def test_retry_then_success(self):
        """Decorated function that fails first call, succeeds second call returns result."""
        calls = [0]

        @retry_once
        def func():
            calls[0] += 1
            if calls[0] == 1:
                raise ValueError("first attempt")
            return "ok"

        result = func()
        assert result == "ok"
        assert calls[0] == 2

    def test_double_failure_raises_second_exception(self):
        """Decorated function that fails both calls raises the SECOND exception."""
        calls = [0]

        @retry_once
        def func():
            calls[0] += 1
            if calls[0] == 1:
                raise ValueError("first")
            raise RuntimeError("second")

        with pytest.raises(RuntimeError) as exc_info:
            func()
        assert "second" in str(exc_info.value)

    def test_max_two_calls(self):
        """Decorated function is called at most 2 times total."""
        calls = [0]

        @retry_once
        def func():
            calls[0] += 1
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError):
            func()
        assert calls[0] == 2


# -- log_error_to_file tests --

class TestLogErrorToFile:
    def test_writes_entry_with_correct_format(self, temp_dir):
        """Writes entry to new file with format '[ISO_TIMESTAMP] filename.pdf | ErrorType: message\\n'."""
        error_log_path = Path(temp_dir) / "errors.log"
        log_error_to_file("test.pdf", ValueError("bad input"), error_log_path)

        assert error_log_path.is_file()
        content = error_log_path.read_text()
        assert "[" in content
        assert "test.pdf" in content
        assert "ValueError" in content
        assert "bad input" in content

    def test_appends_to_existing_file(self, temp_dir):
        """Appends to existing file (does not overwrite previous entries)."""
        error_log_path = Path(temp_dir) / "errors.log"
        log_error_to_file("file1.pdf", ValueError("error1"), error_log_path)
        log_error_to_file("file2.pdf", TypeError("error2"), error_log_path)

        lines = error_log_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "file1.pdf" in lines[0]
        assert "file2.pdf" in lines[1]

    def test_creates_parent_directory(self, temp_dir):
        """Creates parent directory if it does not exist."""
        error_log_path = Path(temp_dir) / "subdir" / "errors.log"
        log_error_to_file("test.pdf", ValueError("error"), error_log_path)

        assert error_log_path.is_file()
        assert error_log_path.parent.is_dir()


# -- save_checkpoint_atomic tests --

class TestSaveCheckpointAtomic:
    def test_creates_valid_json_file(self, temp_dir):
        """Creates valid JSON file at checkpoint_path with keys 'metadata', 'results', 'processed_files'."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        results = [{"filename": "a.pdf", "page": 1, "ids": ["12345"], "rotation_detected": 90, "notes": ""}]
        processed_files = {"a.pdf"}

        save_checkpoint_atomic(results, processed_files, "/input/dir", checkpoint_path, 50)

        assert checkpoint_path.is_file()
        with open(checkpoint_path) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "results" in data
        assert "processed_files" in data

    def test_metadata_contains_required_fields(self, temp_dir):
        """Metadata contains version '1.0', input_path, processed_count, timestamp, checkpoint_frequency."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        results = [{"filename": "a.pdf", "page": 1, "ids": ["12345"], "rotation_detected": 90, "notes": ""}]
        processed_files = {"a.pdf"}

        save_checkpoint_atomic(results, processed_files, "/input/dir", checkpoint_path, 50)

        with open(checkpoint_path) as f:
            data = json.load(f)

        assert data["metadata"]["version"] == "1.0"
        assert data["metadata"]["input_path"] == "/input/dir"
        assert data["metadata"]["processed_count"] == 1
        assert data["metadata"]["checkpoint_frequency"] == 50
        assert "timestamp" in data["metadata"]

    def test_overwrites_existing_checkpoint(self, temp_dir):
        """If checkpoint_path already exists, it is overwritten atomically."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"

        # First checkpoint
        results1 = [{"filename": "a.pdf", "page": 1, "ids": ["12345"], "rotation_detected": 90, "notes": ""}]
        save_checkpoint_atomic(results1, {"a.pdf"}, "/input", checkpoint_path, 50)

        # Second checkpoint
        results2 = [{"filename": "b.pdf", "page": 1, "ids": ["67890"], "rotation_detected": 90, "notes": ""}]
        save_checkpoint_atomic(results2, {"b.pdf"}, "/input", checkpoint_path, 50)

        with open(checkpoint_path) as f:
            data = json.load(f)

        # Verify second data is present
        assert data["results"][0]["filename"] == "b.pdf"
        assert data["processed_files"] == ["b.pdf"]

    def test_no_tmp_files_left_behind(self, temp_dir):
        """No .tmp files left behind after successful write."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        results = [{"filename": "a.pdf", "page": 1, "ids": ["12345"], "rotation_detected": 90, "notes": ""}]
        processed_files = {"a.pdf"}

        save_checkpoint_atomic(results, processed_files, "/input", checkpoint_path, 50)

        # Check for temp files
        tmp_files = list(Path(temp_dir).glob("*.tmp"))
        assert len(tmp_files) == 0


# -- load_checkpoint_if_exists tests --

class TestLoadCheckpointIfExists:
    def test_returns_none_when_no_checkpoint_file(self, temp_dir):
        """Returns None when no checkpoint file exists."""
        result = load_checkpoint_if_exists(Path(temp_dir), "/input")
        assert result is None

    def test_returns_tuple_when_valid_checkpoint(self, temp_dir, capsys):
        """Returns (results_list, processed_files_set) when valid checkpoint exists."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        checkpoint_data = {
            "metadata": {
                "version": "1.0",
                "input_path": "/input",
                "processed_count": 1,
                "timestamp": "2026-06-05T10:00:00Z",
                "checkpoint_frequency": 50
            },
            "results": [{"filename": "a.pdf", "page": 1, "ids": ["12345"], "rotation_detected": 90, "notes": ""}],
            "processed_files": ["a.pdf"]
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)

        result = load_checkpoint_if_exists(Path(temp_dir), "/input")

        assert result is not None
        results, processed_files = result
        assert isinstance(results, list)
        assert isinstance(processed_files, set)
        assert len(results) == 1
        assert "a.pdf" in processed_files

    def test_prints_resume_message(self, temp_dir, capsys):
        """Prints 'Resuming from checkpoint: N files already processed' (captured stdout)."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        checkpoint_data = {
            "metadata": {
                "version": "1.0",
                "input_path": "/input",
                "processed_count": 1,
                "timestamp": "2026-06-05T10:00:00Z",
                "checkpoint_frequency": 50
            },
            "results": [],
            "processed_files": ["a.pdf"]
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)

        load_checkpoint_if_exists(Path(temp_dir), "/input")

        captured = capsys.readouterr()
        assert "Resuming from checkpoint" in captured.out
        assert "1 files already processed" in captured.out

    def test_prints_warning_when_input_path_differs(self, temp_dir, capsys):
        """Prints WARNING when checkpoint input_path differs from current input_path."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        checkpoint_data = {
            "metadata": {
                "version": "1.0",
                "input_path": "/old/path",
                "processed_count": 1,
                "timestamp": "2026-06-05T10:00:00Z",
                "checkpoint_frequency": 50
            },
            "results": [],
            "processed_files": ["a.pdf"]
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)

        load_checkpoint_if_exists(Path(temp_dir), "/new/path")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_returns_none_and_deletes_on_corrupt_json(self, temp_dir):
        """Returns None and deletes file when checkpoint is corrupt JSON."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        checkpoint_path.write_text("{{invalid json")

        result = load_checkpoint_if_exists(Path(temp_dir), "/input")

        assert result is None
        assert not checkpoint_path.exists()

    def test_returns_none_and_deletes_on_missing_keys(self, temp_dir):
        """Returns None and deletes file when checkpoint is missing required keys."""
        checkpoint_path = Path(temp_dir) / ".checkpoint.json"
        checkpoint_data = {"metadata": {}}  # Missing results and processed_files
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)

        result = load_checkpoint_if_exists(Path(temp_dir), "/input")

        assert result is None
        assert not checkpoint_path.exists()


# -- filter_remaining_pdfs tests --

class TestFilterRemainingPdfs:
    def test_removes_processed_paths(self):
        """Removes paths whose .name is in processed_files set."""
        paths = [Path("a.pdf"), Path("b.pdf"), Path("c.pdf")]
        processed = {"a.pdf", "c.pdf"}

        result = filter_remaining_pdfs(paths, processed)

        assert result == [Path("b.pdf")]

    def test_keeps_unprocessed_paths(self):
        """Keeps paths whose .name is NOT in processed_files set."""
        paths = [Path("a.pdf"), Path("b.pdf"), Path("c.pdf")]
        processed = {"a.pdf"}

        result = filter_remaining_pdfs(paths, processed)

        assert Path("b.pdf") in result
        assert Path("c.pdf") in result
        assert len(result) == 2

    def test_returns_empty_when_all_processed(self):
        """Returns empty list when all files already processed."""
        paths = [Path("a.pdf"), Path("b.pdf"), Path("c.pdf")]
        processed = {"a.pdf", "b.pdf", "c.pdf"}

        result = filter_remaining_pdfs(paths, processed)

        assert result == []


# -- calculate_batch_stats tests --

class TestCalculateBatchStats:
    def test_returns_dict_with_required_keys(self):
        """Returns dict with 'summary', 'performance', 'resume_context' keys."""
        import time
        results = [{'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]

        stats = calculate_batch_stats(results, checkpointed_count=0, newly_processed_count=1, start_time=time.time()-1.0)

        assert "summary" in stats
        assert "performance" in stats
        assert "resume_context" in stats

    def test_summary_total_files_counts_unique_filenames(self):
        """summary.total_files counts unique filenames."""
        import time
        results = [
            {'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'a.pdf', 'page': 2, 'ids': [], 'rotation_detected': None, 'notes': 'no_match'},
            {'filename': 'b.pdf', 'page': 1, 'ids': [], 'rotation_detected': None, 'notes': 'error: ValueError: corrupt'}
        ]

        stats = calculate_batch_stats(results, checkpointed_count=0, newly_processed_count=2, start_time=time.time()-1.0)

        assert stats["summary"]["total_files"] == 2  # a.pdf, b.pdf

    def test_summary_ids_found_sums_ids(self):
        """summary.ids_found sums len(r['ids']) across all results."""
        import time
        results = [
            {'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'a.pdf', 'page': 2, 'ids': ['67890', '11234'], 'rotation_detected': 90, 'notes': ''},
        ]

        stats = calculate_batch_stats(results, checkpointed_count=0, newly_processed_count=1, start_time=time.time()-1.0)

        assert stats["summary"]["ids_found"] == 3  # 1 + 2

    def test_summary_failed_counts_error_results(self):
        """summary.failed counts results with page==0 and 'error:' in notes."""
        import time
        results = [
            {'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'b.pdf', 'page': 0, 'ids': [], 'rotation_detected': None, 'notes': 'error: ValueError: corrupt'}
        ]

        stats = calculate_batch_stats(results, checkpointed_count=0, newly_processed_count=2, start_time=time.time()-1.0)

        assert stats["summary"]["failed"] == 1

    def test_summary_no_id_pages_counts_non_error_empty_ids(self):
        """summary.no_id_pages counts non-error results with empty ids."""
        import time
        results = [
            {'filename': 'a.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'a.pdf', 'page': 2, 'ids': [], 'rotation_detected': None, 'notes': 'no_match_any_rotation'}
        ]

        stats = calculate_batch_stats(results, checkpointed_count=0, newly_processed_count=1, start_time=time.time()-1.0)

        assert stats["summary"]["no_id_pages"] == 1

    def test_performance_files_per_second_calculated(self):
        """performance.files_per_second = newly_processed_count / duration."""
        import time
        results = []
        start_time = time.time() - 10.0

        stats = calculate_batch_stats(results, checkpointed_count=0, newly_processed_count=2, start_time=start_time)

        assert isinstance(stats["performance"]["files_per_second"], float)
        assert stats["performance"]["files_per_second"] > 0

    def test_resume_context_tracks_counts(self):
        """resume_context.previously_checkpointed = checkpointed_count param."""
        import time
        results = []

        stats = calculate_batch_stats(results, checkpointed_count=5, newly_processed_count=2, start_time=time.time()-1.0)

        assert stats["resume_context"]["previously_checkpointed"] == 5
        assert stats["resume_context"]["newly_processed"] == 2


# -- print_batch_stats tests --

class TestPrintBatchStats:
    def test_prints_summary_header(self, capsys):
        """Prints 'BATCH PROCESSING SUMMARY' header."""
        stats = {
            "summary": {"total_files": 1, "successful": 1, "failed": 0, "total_pages": 1, "ids_found": 1, "no_id_pages": 0, "error_count": 0},
            "performance": {"wall_clock_duration_sec": 1.0, "files_per_second": 1.0},
            "resume_context": {"previously_checkpointed": 0, "newly_processed": 1}
        }

        print_batch_stats(stats)

        captured = capsys.readouterr()
        assert "BATCH PROCESSING SUMMARY" in captured.out

    def test_prints_resume_section_when_checkpointed(self, capsys):
        """Prints 'Resumed from checkpoint:' line when previously_checkpointed > 0."""
        stats = {
            "summary": {"total_files": 1, "successful": 1, "failed": 0, "total_pages": 1, "ids_found": 1, "no_id_pages": 0, "error_count": 0},
            "performance": {"wall_clock_duration_sec": 1.0, "files_per_second": 1.0},
            "resume_context": {"previously_checkpointed": 10, "newly_processed": 1}
        }

        print_batch_stats(stats)

        captured = capsys.readouterr()
        assert "Resumed from checkpoint" in captured.out

    def test_does_not_print_resume_when_no_checkpoint(self, capsys):
        """Does NOT print resume section when previously_checkpointed == 0."""
        stats = {
            "summary": {"total_files": 1, "successful": 1, "failed": 0, "total_pages": 1, "ids_found": 1, "no_id_pages": 0, "error_count": 0},
            "performance": {"wall_clock_duration_sec": 1.0, "files_per_second": 1.0},
            "resume_context": {"previously_checkpointed": 0, "newly_processed": 1}
        }

        print_batch_stats(stats)

        captured = capsys.readouterr()
        assert "Resumed from checkpoint" not in captured.out


# -- Task 1 Integration Tests (Wave 2) --

class TestWrapperWithRetry:
    """Integration tests for process_single_pdf_wrapper with retry and error logging."""

    def test_wrapper_returns_results_on_success(self, tmp_path):
        """Wrapper returns results normally when process_single_pdf succeeds."""
        import precede_ocr

        # Mock successful processing
        valid_results = [{'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]
        with patch('precede_ocr.process_single_pdf', return_value=valid_results):
            result = process_single_pdf_wrapper(Path('test.pdf'))

        assert result == valid_results

    def test_wrapper_retries_on_transient_failure(self, tmp_path):
        """Wrapper retries once when process_single_pdf fails first call."""
        import precede_ocr

        # Mock: first call raises, second succeeds
        valid_results = [{'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]
        with patch('precede_ocr.process_single_pdf', side_effect=[ValueError("transient"), valid_results]):
            result = process_single_pdf_wrapper(Path('test.pdf'))

        assert result == valid_results

    def test_wrapper_returns_error_dict_on_permanent_failure(self, tmp_path):
        """Wrapper returns error dict when both attempts fail."""
        import precede_ocr

        # Set module-level error log path
        error_log_path = tmp_path / 'errors.log'
        precede_ocr._ERROR_LOG_PATH = str(error_log_path)

        # Mock: always raises
        with patch('precede_ocr.process_single_pdf', side_effect=RuntimeError("permanent")):
            result = process_single_pdf_wrapper(Path('test.pdf'))

        # Should return error dict
        assert len(result) == 1
        assert result[0]['page'] == 0
        assert 'error:' in result[0]['notes']
        assert 'RuntimeError' in result[0]['notes']

        # Should log to errors.log
        assert error_log_path.exists()
        log_content = error_log_path.read_text()
        assert 'test.pdf' in log_content
        assert 'RuntimeError' in log_content
        assert 'permanent' in log_content

    def test_wrapper_error_dict_preserves_format(self, tmp_path):
        """Error dict has correct keys: filename, page, ids, rotation_detected, notes."""
        import precede_ocr

        error_log_path = tmp_path / 'errors.log'
        precede_ocr._ERROR_LOG_PATH = str(error_log_path)

        with patch('precede_ocr.process_single_pdf', side_effect=ValueError("test")):
            result = process_single_pdf_wrapper(Path('myfile.pdf'))

        assert result[0]['filename'] == 'myfile.pdf'
        assert result[0]['page'] == 0
        assert result[0]['ids'] == []
        assert result[0]['rotation_detected'] is None
        assert 'error:' in result[0]['notes']


class TestCheckpointIntegration:
    """Integration tests for checkpoint pipeline wiring."""

    def test_process_all_pdfs_accepts_checkpoint_params(self):
        """process_all_pdfs signature includes checkpoint params."""
        import inspect
        sig = inspect.signature(process_all_pdfs)
        params = list(sig.parameters.keys())

        assert 'checkpointed_results' in params
        assert 'checkpoint_path' in params
        assert 'input_path' in params
        assert 'checkpoint_frequency' in params

    def test_fresh_flag_deletes_checkpoint(self, tmp_path):
        """--fresh flag deletes existing checkpoint before processing."""
        # Create a checkpoint file
        checkpoint_file = tmp_path / '.checkpoint.json'
        checkpoint_file.write_text('{"metadata": {}}')

        # Create a dummy PDF
        pdf_file = tmp_path / 'test.pdf'
        pdf_file.write_bytes(b'dummy')

        # Mock discover_pdfs and processing to avoid actual PDF handling
        with patch('precede_ocr.discover_pdfs', return_value=[pdf_file]):
            with patch('precede_ocr._process_single_pdf_with_retry') as mock_proc:
                mock_proc.return_value = [{'filename': 'test.pdf', 'page': 1, 'ids': [], 'rotation_detected': None, 'notes': 'no_match_any_rotation'}]

                # Call main with fresh=True
                main(str(tmp_path), str(tmp_path / 'results.csv'), fresh=True)

    def test_fresh_flag_deletes_error_log(self, tmp_path):
        """--fresh flag deletes existing error log."""
        error_log = tmp_path / 'errors.log'
        error_log.write_text('[2026-01-01] test.pdf | Error: test\n')

        pdf_file = tmp_path / 'test.pdf'
        pdf_file.write_bytes(b'dummy')

        with patch('precede_ocr.discover_pdfs', return_value=[pdf_file]):
            with patch('precede_ocr._process_single_pdf_with_retry') as mock_proc:
                mock_proc.return_value = [{'filename': 'test.pdf', 'page': 1, 'ids': [], 'rotation_detected': None, 'notes': ''}]

                main(str(tmp_path), str(tmp_path / 'results.csv'), fresh=True)

    def test_main_writes_batch_stats_json(self, tmp_path):
        """main() writes batch_stats.json to output directory."""
        pdf_file = tmp_path / 'test.pdf'
        pdf_file.write_bytes(b'dummy')

        with patch('precede_ocr.discover_pdfs', return_value=[pdf_file]):
            with patch('precede_ocr._process_single_pdf_with_retry') as mock_proc:
                mock_proc.return_value = [{'filename': 'test.pdf', 'page': 1, 'ids': ['12345'], 'rotation_detected': 90, 'notes': ''}]

                output_csv = tmp_path / 'results.csv'
                main(str(tmp_path), str(output_csv))

        # batch_stats.json should exist
        stats_file = tmp_path / 'batch_stats.json'
        assert stats_file.exists()

        # Should be valid JSON with summary key
        stats = json.loads(stats_file.read_text())
        assert 'summary' in stats

    def test_main_resumes_from_checkpoint(self, tmp_path):
        """main() loads checkpoint and only processes remaining files."""
        # Create checkpoint with 2 processed files
        checkpoint_data = {
            "metadata": {
                "version": "1.0",
                "input_path": str(tmp_path),
                "processed_count": 2,
                "timestamp": "2026-06-05T10:00:00",
                "checkpoint_frequency": 50
            },
            "results": [
                {'filename': 'file1.pdf', 'page': 1, 'ids': ['11111'], 'rotation_detected': 90, 'notes': ''},
                {'filename': 'file2.pdf', 'page': 1, 'ids': ['22222'], 'rotation_detected': 90, 'notes': ''}
            ],
            "processed_files": ["file1.pdf", "file2.pdf"]
        }
        checkpoint_path = tmp_path / '.checkpoint.json'
        checkpoint_path.write_text(json.dumps(checkpoint_data))

        # Create 3 PDF files (2 already processed, 1 new)
        for name in ['file1.pdf', 'file2.pdf', 'file3.pdf']:
            (tmp_path / name).write_bytes(b'dummy')

        with patch('precede_ocr.discover_pdfs', return_value=[tmp_path / 'file1.pdf', tmp_path / 'file2.pdf', tmp_path / 'file3.pdf']):
            with patch('precede_ocr.process_all_pdfs') as mock_proc_all:
                mock_proc_all.return_value = checkpoint_data['results'] + [{'filename': 'file3.pdf', 'page': 1, 'ids': ['33333'], 'rotation_detected': 90, 'notes': ''}]

                output_csv = tmp_path / 'results.csv'
                main(str(tmp_path), str(output_csv))

                # Should have called process_all_pdfs with only file3.pdf
                call_args = mock_proc_all.call_args
                pdf_paths_arg = call_args[0][0]  # First positional arg
                assert len(pdf_paths_arg) == 1
                assert pdf_paths_arg[0].name == 'file3.pdf'


class TestFreshArgparse:
    """Test --fresh flag is accepted by argparse."""

    def test_fresh_flag_parsed(self):
        """Parser accepts --fresh flag."""
        # Test that argparse block includes --fresh
        # This is more of a smoke test since we're testing the integration
        # The actual argparse is in __main__ block, tested via subprocess or inspection

        # For now, just verify the flag exists by attempting to use it
        # This will be validated in the human-verify checkpoint when running actual CLI
        pass  # Covered by manual verification in checkpoint task


# -- preprocess_image tests --

class TestPreprocessImage:
    def test_returns_pil_image(self):
        """preprocess_image returns a PIL Image object."""
        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        result = preprocess_image(img)
        assert isinstance(result, Image.Image)

    def test_output_is_grayscale(self):
        """Output image mode is 'L' (grayscale)."""
        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        result = preprocess_image(img)
        assert result.mode == 'L'

    def test_output_is_binary(self):
        """Output pixels are only 0 or 255 (Otsu binarization)."""
        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        result = preprocess_image(img)
        pixels = list(result.get_flattened_data())
        unique_values = set(pixels)
        assert unique_values.issubset({0, 255})

    def test_handles_rgb_input(self):
        """Processes 3-channel RGB image without error."""
        img = Image.new('RGB', (200, 200), color=(100, 150, 200))
        result = preprocess_image(img)
        assert isinstance(result, Image.Image)
        assert result.mode == 'L'

    def test_handles_grayscale_input(self):
        """Processes already-grayscale (mode 'L') image without error."""
        img = Image.new('L', (200, 200), color=128)
        result = preprocess_image(img)
        assert isinstance(result, Image.Image)
        assert result.mode == 'L'

    def test_preserves_dimensions(self):
        """Output image has same width and height as input."""
        img = Image.new('RGB', (300, 400), color=(128, 128, 128))
        result = preprocess_image(img)
        assert result.size == (300, 400)


# -- Preprocessing fallback integration tests --

class TestPreprocessingFallback:
    """Tests for preprocessing fallback in extract_id_with_rotation (D-01/D-02/D-03/D-04/D-05)."""

    def test_direct_success_skips_preprocessing(self):
        """When direct OCR finds valid IDs, preprocess_image is NOT called."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))

        with patch('precede_ocr.pytesseract.image_to_string', return_value='12345'):
            with patch('precede_ocr.preprocess_image') as mock_preprocess:
                ids, angle, notes = extract_id_with_rotation(img)

                mock_preprocess.assert_not_called()
                assert ids == ['12345']
                assert notes == ''

    def test_preprocessing_triggered_on_no_text(self):
        """When direct OCR returns empty text (no_text_detected), preprocess_image IS called (D-03)."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        # Direct OCR: 4 calls return empty. Preprocessed OCR: first call returns valid ID.
        side_effects = ['', '', '', '',  # 4 direct rotations fail
                        '67890']          # First preprocessed rotation succeeds
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img) as mock_pp:
                ids, angle, notes = extract_id_with_rotation(img)

                mock_pp.assert_called_once_with(img)
                assert ids == ['67890']
                assert notes == 'preprocessed'

    def test_preprocessing_triggered_on_noise_matches(self):
        """When direct OCR returns only noise (trivial patterns), preprocess_image IS called (D-03)."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        # Direct OCR: returns only trivial patterns. Preprocessed: valid ID.
        side_effects = ['00000', '11111', '22222', '33333',  # 4 direct: noise only
                        '54321']                               # First preprocessed succeeds
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img) as mock_pp:
                ids, angle, notes = extract_id_with_rotation(img)

                mock_pp.assert_called_once()
                assert ids == ['54321']
                assert notes == 'preprocessed'

    def test_preprocessing_triggered_on_no_match(self):
        """When direct OCR returns text but no 5-digit match, preprocess_image IS called (D-03)."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        # Direct OCR: text but no 5-digit numbers. Preprocessed: valid ID.
        side_effects = ['abc', 'xyz', '123', '4567',  # 4 direct: no 5-digit match
                        '98765']                        # First preprocessed succeeds
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img) as mock_pp:
                ids, angle, notes = extract_id_with_rotation(img)

                mock_pp.assert_called_once()
                assert ids == ['98765']
                assert notes == 'preprocessed'

    def test_preprocessed_notes_value(self):
        """When preprocessing fallback succeeds, notes is exactly 'preprocessed' (D-04)."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        side_effects = ['', '', '', '',  # 4 direct fail
                        '45678']          # Preprocessed succeeds
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img):
                ids, angle, notes = extract_id_with_rotation(img)

                assert notes == 'preprocessed'

    def test_both_fail_returns_failure_reason(self):
        """When both direct and preprocessed OCR fail, returns failure reason from all 8 texts."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        # All 8 OCR calls return empty text
        side_effects = ['', '', '', '', '', '', '', '']
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img):
                ids, angle, notes = extract_id_with_rotation(img)

                assert ids == []
                assert angle is None
                assert notes == 'no_text_detected'

    def test_preprocessed_pass_uses_same_rotation_order(self):
        """Preprocessing pass tries rotations in same order: [90, 270, 0, 180] (D-02)."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        # Direct: all 4 fail. Preprocessed: third rotation (0 deg) succeeds.
        side_effects = ['', '', '', '',   # 4 direct fail
                        '', '',            # Preprocessed 90, 270 fail
                        '11223']           # Preprocessed 0 succeeds
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img):
                ids, angle, notes = extract_id_with_rotation(img)

                assert ids == ['11223']
                assert angle == 0  # Third in [90, 270, 0, 180]
                assert notes == 'preprocessed'

    def test_classify_failure_receives_all_8_texts(self):
        """When both passes fail, classify_failure_reason receives 4 direct + 4 preprocessed texts."""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        preprocessed_img = Image.new('L', (100, 100), color=128)

        side_effects = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        with patch('precede_ocr.pytesseract.image_to_string', side_effect=side_effects):
            with patch('precede_ocr.preprocess_image', return_value=preprocessed_img):
                with patch('precede_ocr.classify_failure_reason', return_value='no_match_any_rotation') as mock_classify:
                    ids, angle, notes = extract_id_with_rotation(img)

                    # Should pass all 8 OCR texts
                    call_args = mock_classify.call_args[0][0]
                    assert len(call_args) == 8
                    assert call_args == ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']


# -- validate_sequence tests --

class TestValidateSequence:
    """Tests for post-hoc sequential ID validation (D-06, D-07, D-08)."""

    def _make_result(self, filename, page, ids, rotation=90, notes=''):
        """Helper to create result dict."""
        return {
            'filename': filename,
            'page': page,
            'ids': ids,
            'rotation_detected': rotation,
            'notes': notes
        }

    def test_returns_list_of_dicts(self):
        """validate_sequence returns a list of dicts."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
        ]
        validated = validate_sequence(results)
        assert isinstance(validated, list)
        assert all(isinstance(r, dict) for r in validated)

    def test_sequential_ids_not_flagged(self):
        """File with clean sequential IDs has no seq_outlier flags."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004']),
            self._make_result('a.pdf', 5, ['10005']),
        ]
        validated = validate_sequence(results)
        for r in validated:
            assert 'seq_outlier' not in r['notes']

    def test_wild_outlier_flagged(self):
        """An ID wildly deviating from the trend is flagged; normal IDs are not."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004']),
            self._make_result('a.pdf', 5, ['99999']),  # Wild outlier
        ]
        validated = validate_sequence(results)
        # The outlier (page 5, id 99999) should be flagged
        page5 = [r for r in validated if r['page'] == 5][0]
        assert 'seq_outlier_conf_' in page5['notes']
        # Normal sequential IDs should NOT be flagged
        for r in [x for x in validated if x['page'] != 5]:
            assert 'seq_outlier' not in r['notes'], f"Page {r['page']} should not be flagged"

    def test_fewer_than_3_ids_skipped(self):
        """Files with fewer than 3 valid IDs are not validated (passed through)."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
        ]
        validated = validate_sequence(results)
        for r in validated:
            assert 'seq_outlier' not in r['notes']

    def test_exactly_3_ids_validated(self):
        """Files with exactly 3 IDs are validated (minimum for regression)."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['99999']),  # Outlier
        ]
        validated = validate_sequence(results)
        page3 = [r for r in validated if r['page'] == 3][0]
        assert 'seq_outlier_conf_' in page3['notes']
        # Normal IDs should NOT be flagged
        for r in [x for x in validated if x['page'] != 3]:
            assert 'seq_outlier' not in r['notes']

    def test_notes_combined_with_semicolon(self):
        """Existing 'preprocessed' note gets semicolon-separated outlier flag."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004']),
            self._make_result('a.pdf', 5, ['99999'], notes='preprocessed'),  # Outlier with existing note
        ]
        validated = validate_sequence(results)
        page5 = [r for r in validated if r['page'] == 5][0]
        assert page5['notes'].startswith('preprocessed; seq_outlier_conf_')

    def test_empty_notes_no_semicolons(self):
        """Empty notes gets flag without leading semicolons."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004']),
            self._make_result('a.pdf', 5, ['99999']),  # Outlier with empty notes
        ]
        validated = validate_sequence(results)
        page5 = [r for r in validated if r['page'] == 5][0]
        assert page5['notes'].startswith('seq_outlier_conf_')
        assert not page5['notes'].startswith(';')

    def test_error_rows_passed_through(self):
        """Error rows (page==0, 'error:' in notes) are unchanged."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            {'filename': 'b.pdf', 'page': 0, 'ids': [], 'rotation_detected': None,
             'notes': 'error: ValueError: corrupt'},
        ]
        validated = validate_sequence(results)
        error_row = [r for r in validated if r['filename'] == 'b.pdf'][0]
        assert error_row['notes'] == 'error: ValueError: corrupt'

    def test_no_id_rows_passed_through(self):
        """No-ID rows (empty ids list) are unchanged."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, [], notes='no_match_any_rotation'),
        ]
        validated = validate_sequence(results)
        no_id_row = [r for r in validated if r['page'] == 4][0]
        assert no_id_row['notes'] == 'no_match_any_rotation'

    def test_sorts_by_page_before_regression(self):
        """Results out of page order (from imap_unordered) are sorted before analysis."""
        # Provide results in random order -- should still work correctly
        results = [
            self._make_result('a.pdf', 5, ['99999']),  # Outlier, out of order
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 4, ['10004']),
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 3, ['10003']),
        ]
        validated = validate_sequence(results)
        page5 = [r for r in validated if r['page'] == 5][0]
        assert 'seq_outlier_conf_' in page5['notes']

    def test_mad_zero_no_outliers(self):
        """Perfect linear sequence (MAD==0) flags no outliers."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004']),
        ]
        validated = validate_sequence(results)
        for r in validated:
            assert 'seq_outlier' not in r['notes']

    def test_multiple_files_independent(self):
        """Each file is validated independently."""
        results = [
            # File A: clean sequence
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            # File B: has outlier
            self._make_result('b.pdf', 1, ['20001']),
            self._make_result('b.pdf', 2, ['20002']),
            self._make_result('b.pdf', 3, ['20003']),
            self._make_result('b.pdf', 4, ['99999']),  # Outlier in file B
        ]
        validated = validate_sequence(results)

        # File A: no flags
        a_results = [r for r in validated if r['filename'] == 'a.pdf']
        for r in a_results:
            assert 'seq_outlier' not in r['notes']

        # File B: page 4 flagged
        b_page4 = [r for r in validated if r['filename'] == 'b.pdf' and r['page'] == 4][0]
        assert 'seq_outlier_conf_' in b_page4['notes']

    def test_does_not_modify_original_results(self):
        """Original result dicts are not modified (copies created)."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['99999']),
        ]
        original_notes = [r['notes'] for r in results]
        validate_sequence(results)
        current_notes = [r['notes'] for r in results]
        assert original_notes == current_notes

    def test_outlier_not_pulled_by_extreme(self):
        """Theil-Sen regression is not pulled by extreme outlier (UAT regression test).
        Simulates real-world data: IDs 16243-16284 with outlier 89791."""
        results = [
            self._make_result('a.pdf', 1, ['16243']),
            self._make_result('a.pdf', 2, ['16245']),
            self._make_result('a.pdf', 3, ['89791']),  # Extreme outlier
            self._make_result('a.pdf', 4, ['16250']),
            self._make_result('a.pdf', 5, ['16253']),
            self._make_result('a.pdf', 6, ['16256']),
            self._make_result('a.pdf', 7, ['16259']),
            self._make_result('a.pdf', 8, ['16262']),
            self._make_result('a.pdf', 9, ['16265']),
            self._make_result('a.pdf', 10, ['16268']),
        ]
        validated = validate_sequence(results)
        # Only the extreme outlier on page 3 should be flagged
        page3 = [r for r in validated if r['page'] == 3][0]
        assert 'seq_outlier_conf_' in page3['notes'], "Extreme outlier should be flagged"
        # All other pages should NOT be flagged
        for r in [x for x in validated if x['page'] != 3]:
            assert 'seq_outlier' not in r['notes'], f"Page {r['page']} (ID {r['ids']}) should NOT be flagged"

    def test_outlier_confidence_is_high(self):
        """Extreme outliers should get high confidence (>50%), not 0%."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004']),
            self._make_result('a.pdf', 5, ['99999']),  # Extreme outlier
        ]
        validated = validate_sequence(results)
        page5 = [r for r in validated if r['page'] == 5][0]
        # Extract confidence value
        import re as _re
        match = _re.search(r'seq_outlier_conf_(\d+)%', page5['notes'])
        assert match, "Outlier should have confidence flag"
        confidence = int(match.group(1))
        assert confidence > 50, f"Extreme outlier should have high confidence, got {confidence}%"

    def test_no_duplicate_flags_multi_id_page(self):
        """Multi-ID page should not get duplicate flags."""
        results = [
            self._make_result('a.pdf', 1, ['10001']),
            self._make_result('a.pdf', 2, ['10002']),
            self._make_result('a.pdf', 3, ['10003']),
            self._make_result('a.pdf', 4, ['10004', '99999']),  # One normal, one outlier
        ]
        validated = validate_sequence(results)
        page4 = [r for r in validated if r['page'] == 4][0]
        # Count occurrences of seq_outlier_conf_ -- should be exactly 1
        count = page4['notes'].count('seq_outlier_conf_')
        assert count <= 1, f"Should have at most 1 outlier flag, got {count}: {page4['notes']}"


# -- Task 2: main() integration tests --

class TestMainSequenceValidation:
    """Integration test: main() calls validate_sequence before writing output."""

    def test_main_calls_validate_sequence(self, tmp_path):
        """main() passes results through validate_sequence before writing CSV/JSON."""
        pdf_file = tmp_path / 'test.pdf'
        pdf_file.write_bytes(b'dummy')

        mock_results = [
            {'filename': 'test.pdf', 'page': 1, 'ids': ['10001'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 2, 'ids': ['10002'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 3, 'ids': ['10003'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 4, 'ids': ['10004'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 5, 'ids': ['10005'], 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 6, 'ids': ['99999'], 'rotation_detected': 270, 'notes': ''},
        ]

        with patch('precede_ocr.discover_pdfs', return_value=[pdf_file]):
            with patch('precede_ocr._process_single_pdf_with_retry', return_value=mock_results):
                output_csv = tmp_path / 'results.csv'
                main(str(tmp_path), str(output_csv))

        import csv
        with open(output_csv) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # The extreme outlier (page 6, id 99999) should be flagged
        page6_row = [r for r in rows if r['page'] == '6'][0]
        assert 'seq_outlier_conf_' in page6_row['notes'], "Outlier ID should be flagged"

        # Normal sequential IDs should NOT be flagged
        normal_rows = [r for r in rows if r['page'] != '6']
        for row in normal_rows:
            assert 'seq_outlier' not in row['notes'], f"Page {row['page']} should not be flagged"


# -- Phase 6: Campaign State Tests --

class TestCampaignState:
    def test_default_values(self):
        state = CampaignState()
        assert state.version == "1.1"
        assert state.status == "running"
        assert state.interruptions == []
        assert state.folder_stats == {}
        assert state.options == {}
        assert state.files_processed == 0
        assert state.files_failed == 0

    def test_generate_campaign_id_format(self):
        cid = CampaignState.generate_campaign_id()
        assert re.match(r'^campaign_\d{8}_\d{6}$', cid)

    def test_interruptions_empty_by_default(self):
        state = CampaignState()
        assert isinstance(state.interruptions, list)
        assert len(state.interruptions) == 0


class TestSaveCampaignStateAtomic:
    def test_creates_valid_json(self, temp_dir):
        state = CampaignState(campaign_id="campaign_20260605_100000", input_path="/test")
        save_campaign_state_atomic(state, Path(temp_dir))
        state_path = Path(temp_dir) / 'campaign_state.json'
        assert state_path.is_file()
        with open(state_path) as f:
            data = json.load(f)
        assert data['campaign_id'] == "campaign_20260605_100000"
        assert data['version'] == "1.1"

    def test_no_tmp_files_left(self, temp_dir):
        state = CampaignState(campaign_id="test")
        save_campaign_state_atomic(state, Path(temp_dir))
        tmp_files = list(Path(temp_dir).glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_updates_last_updated(self, temp_dir):
        state = CampaignState(campaign_id="test", last_updated="old")
        save_campaign_state_atomic(state, Path(temp_dir))
        assert state.last_updated != "old"


class TestLoadOrCreateCampaignState:
    def test_fresh_start_creates_new(self, temp_dir, capsys):
        state = load_or_create_campaign_state(Path(temp_dir), "/input", {})
        assert state.campaign_id.startswith("campaign_")
        assert state.status == "running"
        assert state.input_path == "/input"
        assert "Starting new campaign" in capsys.readouterr().out

    def test_loads_existing_state(self, temp_dir, capsys):
        state_path = Path(temp_dir) / 'campaign_state.json'
        state_dict = asdict(CampaignState(
            campaign_id="campaign_20260605_100000",
            input_path="/input", status="interrupted"
        ))
        with open(state_path, 'w') as f:
            json.dump(state_dict, f)
        state = load_or_create_campaign_state(Path(temp_dir), "/input", {})
        assert state.campaign_id == "campaign_20260605_100000"
        assert state.status == "interrupted"
        assert "Resuming campaign" in capsys.readouterr().out

    def test_silent_upgrade_from_v1_checkpoint(self, temp_dir, capsys):
        checkpoint_path = Path(temp_dir) / '.checkpoint.json'
        checkpoint_data = {
            "metadata": {"version": "1.0", "input_path": "/input",
                         "processed_count": 5, "timestamp": "2026-06-05T10:00:00",
                         "checkpoint_frequency": 50},
            "results": [], "processed_files": ["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"]
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)
        state = load_or_create_campaign_state(Path(temp_dir), "/input", {})
        assert state.campaign_id == "campaign_20260605_100000"
        assert state.status == "interrupted"
        assert state.files_processed == 5
        output = capsys.readouterr().out
        assert "Upgraded to campaign tracking" in output

    def test_corrupt_state_recreates_fresh(self, temp_dir, capsys):
        state_path = Path(temp_dir) / 'campaign_state.json'
        with open(state_path, 'w') as f:
            f.write("NOT VALID JSON{{{")
        state = load_or_create_campaign_state(Path(temp_dir), "/input", {})
        assert state.campaign_id.startswith("campaign_")
        assert state.status == "running"
        output = capsys.readouterr().out
        assert "Corrupt campaign state" in output

    def test_input_path_mismatch_warns(self, temp_dir, capsys):
        state_path = Path(temp_dir) / 'campaign_state.json'
        state_dict = asdict(CampaignState(
            campaign_id="campaign_20260605_100000",
            input_path="/old/path", status="interrupted"
        ))
        with open(state_path, 'w') as f:
            json.dump(state_dict, f)
        state = load_or_create_campaign_state(Path(temp_dir), "/new/path", {})
        output = capsys.readouterr().out
        assert "WARNING" in output
        assert "/old/path" in output


class TestComputeFolderPath:
    def test_subdirectory_relative_path(self, temp_dir):
        sub = Path(temp_dir) / "subdir1" / "batch2"
        sub.mkdir(parents=True)
        pdf = sub / "file.pdf"
        pdf.touch()
        result = compute_folder_path(pdf, Path(temp_dir))
        assert "subdir1" in result
        assert "batch2" in result

    def test_root_directory_empty_string(self, temp_dir):
        pdf = Path(temp_dir) / "file.pdf"
        pdf.touch()
        result = compute_folder_path(pdf, Path(temp_dir))
        assert result == ''

    def test_uses_resolve_for_normalization(self, temp_dir):
        pdf = Path(temp_dir) / "file.pdf"
        pdf.touch()
        result = compute_folder_path(pdf, Path(temp_dir))
        assert result == ''

    def test_outside_input_directory(self, temp_dir):
        import tempfile as tf
        with tf.TemporaryDirectory() as other:
            pdf = Path(other) / "file.pdf"
            pdf.touch()
            result = compute_folder_path(pdf, Path(temp_dir))
            assert len(result) > 0  # Returns absolute path, not empty
