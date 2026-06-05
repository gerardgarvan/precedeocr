import pytest
import csv
import sys
import io
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock

from precede_ocr import (
    normalize_digits,
    select_most_likely_id,
    extract_id_with_rotation,
    write_results_csv,
    classify_failure_reason,
    print_rotation_summary,
)


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
        results = [{'filename': 'a.pdf', 'page': 1, 'id': '12345', 'rotation_detected': 0, 'notes': ''}]
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
        """Verify notes column has failure reason for rows where id is None."""
        output_path = str(Path(temp_dir) / "test_output.csv")
        write_results_csv(sample_results, output_path)
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # Skip headers
            rows = list(reader)

        # Page 2 has no ID (None), should have failure reason in notes
        page2_row = rows[1]
        assert page2_row[2] == ''  # id column is empty
        assert page2_row[4] == 'no_text_detected'  # notes column has reason

    def test_csv_notes_empty_for_match(self, sample_results, temp_dir):
        """Verify notes column is empty string for rows where id is not None."""
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


# -- extract_id_with_rotation tests --

class TestExtractIdWithRotation:
    def test_returns_tuple(self):
        """Verify function returns a 3-tuple regardless of input."""
        img = Image.new("RGB", (100, 50), color="white")
        result = extract_id_with_rotation(img)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_blank_image_returns_none(self):
        """A blank white image should yield no ID."""
        img = Image.new("RGB", (200, 100), color="white")
        id_found, rotation, notes = extract_id_with_rotation(img)
        assert id_found is None
        assert rotation is None
        assert notes == 'no_text_detected'

    def test_rotation_order(self):
        """Verify rotation order is [90, 270, 0, 180] and 90 is tried first."""
        img = Image.new("RGB", (100, 50), color="white")

        # Mock pytesseract to return '12345' only when called at 90 degrees
        # Track which rotation angles are tested
        call_count = [0]
        angles_tested = []

        def mock_ocr(image, config=None):
            call_count[0] += 1
            # The rotation order should be [90, 270, 0, 180]
            # We return '12345' on the first call (90 degrees)
            if call_count[0] == 1:
                angles_tested.append('first_call')
                return '12345'
            else:
                angles_tested.append(f'call_{call_count[0]}')
                return ''

        with patch('precede_ocr.pytesseract.image_to_string', side_effect=mock_ocr):
            id_found, rotation, notes = extract_id_with_rotation(img)

        assert id_found == '12345'
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
            id_found, rotation, notes = extract_id_with_rotation(img)

        assert call_count[0] == 1  # Only one call made
        assert id_found == '12345'
        assert rotation == 90

    def test_fallback_to_later_angles(self):
        """Verify fallback to 0 degrees when 90 and 270 return no match."""
        img = Image.new("RGB", (100, 50), color="white")

        call_count = [0]

        def mock_ocr(image, config=None):
            call_count[0] += 1
            # Return empty for 90, 270, then '12345' at 0 degrees (3rd call)
            if call_count[0] == 3:
                return '12345'
            return ''

        with patch('precede_ocr.pytesseract.image_to_string', side_effect=mock_ocr):
            id_found, rotation, notes = extract_id_with_rotation(img)

        assert id_found == '12345'
        assert rotation == 0  # Found at 0 degrees (3rd in order)
        assert notes == ''

    def test_returns_three_values(self):
        """Verify return is now a 3-tuple (id, angle, notes)."""
        img = Image.new("RGB", (100, 50), color="white")

        with patch('precede_ocr.pytesseract.image_to_string', return_value=''):
            result = extract_id_with_rotation(img)

        assert isinstance(result, tuple)
        assert len(result) == 3
        id_found, rotation, notes = result
        assert id_found is None
        assert rotation is None
        assert isinstance(notes, str)


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
            {'filename': 'test.pdf', 'page': 1, 'id': '12345', 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 2, 'id': '67890', 'rotation_detected': 90, 'notes': ''},
            {'filename': 'test.pdf', 'page': 3, 'id': '11111', 'rotation_detected': 0, 'notes': ''},
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
            {'filename': 'test.pdf', 'page': 1, 'id': None, 'rotation_detected': None, 'notes': 'no_text_detected'},
        ]

        print_rotation_summary(results)

        captured = capsys.readouterr()
        output = captured.out
        assert 'No match' in output or 'None' in output
