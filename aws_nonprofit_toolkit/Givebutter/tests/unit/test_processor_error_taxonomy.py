"""Unit tests for processor upload error taxonomy."""

import csv

import pytest

from scripts.processor import (
    EncodingError,
    EmptyCSVError,
    MalformedCSVError,
    UnsupportedGivebutterCSVError,
    process_csv,
)


class TestProcessorErrorTaxonomy:
    """Processor should raise stable exceptions for upload failure categories."""

    def test_non_givebutter_csv_raises_unsupported_error(self, tmp_path):
        input_file = tmp_path / "non_givebutter.csv"
        output_file = tmp_path / "output.csv"
        input_file.write_text("foo,bar,baz\n1,2,3\n", encoding="utf-8")

        with pytest.raises(UnsupportedGivebutterCSVError):
            process_csv(str(input_file), str(output_file))

        assert not output_file.exists()

    def test_missing_required_columns_raises_unsupported_error(self, tmp_path):
        input_file = tmp_path / "missing_columns.csv"
        output_file = tmp_path / "output.csv"
        input_file.write_text("Name,Email,Amount\nJohn Smith,john@example.com,100.00\n", encoding="utf-8")

        with pytest.raises(UnsupportedGivebutterCSVError):
            process_csv(str(input_file), str(output_file))

        assert not output_file.exists()

    def test_empty_csv_raises_empty_error(self, tmp_path):
        input_file = tmp_path / "empty.csv"
        output_file = tmp_path / "output.csv"
        input_file.write_text("", encoding="utf-8")

        with pytest.raises(EmptyCSVError):
            process_csv(str(input_file), str(output_file))

        assert not output_file.exists()

    def test_malformed_csv_raises_malformed_error(self, tmp_path, monkeypatch):
        input_file = tmp_path / "malformed.csv"
        output_file = tmp_path / "output.csv"
        input_file.write_text('Donation ID,Date,Donor Name\n"unterminated,2026-07-14,Jane Doe\n', encoding="utf-8")

        class BrokenReader:
            def __iter__(self):
                return self

            def __next__(self):
                raise csv.Error("malformed csv")

        monkeypatch.setattr("scripts.processor.csv.reader", lambda *args, **kwargs: BrokenReader())

        with pytest.raises(MalformedCSVError):
            process_csv(str(input_file), str(output_file))

        assert not output_file.exists()

    def test_unsupported_encoding_raises_encoding_error(self, tmp_path):
        input_file = tmp_path / "encoding.csv"
        output_file = tmp_path / "output.csv"
        input_file.write_bytes(b"\xff\xfe\x00\x00")

        with pytest.raises(EncodingError):
            process_csv(str(input_file), str(output_file))

        assert not output_file.exists()
