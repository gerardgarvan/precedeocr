import pytest
import csv
from pathlib import Path
from PIL import Image

from precede_ocr import (
    normalize_digits,
    select_most_likely_id,
    extract_id_with_rotation,
    write_results_csv,
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
        assert headers == ["filename", "page", "id", "rotation_detected"]

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
        results = [{'filename': 'a.pdf', 'page': 1, 'id': '12345', 'rotation_detected': 0}]
        write_results_csv(results, output_path)
        assert Path(output_path).is_file()


# -- extract_id_with_rotation tests --

class TestExtractIdWithRotation:
    def test_returns_tuple(self):
        """Verify function returns a 2-tuple regardless of input."""
        img = Image.new("RGB", (100, 50), color="white")
        result = extract_id_with_rotation(img)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_blank_image_returns_none(self):
        """A blank white image should yield no ID."""
        img = Image.new("RGB", (200, 100), color="white")
        id_found, rotation = extract_id_with_rotation(img)
        assert id_found is None
        assert rotation is None
