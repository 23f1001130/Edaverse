"""Reader parity matters: native Excel readers differ in offsets and cell types."""
import datetime as dt
import io

import pytest
from openpyxl import Workbook

from app.services import excel


def _convert(source, reader, monkeypatch, header_row=None):
    monkeypatch.setenv("XLSX_READER", reader)
    output = io.StringIO(newline="")
    result = excel.write_xlsx_csv(source, len(source.getvalue()), output, header_row)
    return output.getvalue(), result


def _workbook():
    book = Workbook()
    sheet = book.active
    sheet["B3"] = "code"
    sheet["C3"] = "value"
    sheet["D3"] = "date"
    sheet.append([None, "001", 1, dt.date(2026, 10, 28)])
    sheet.append([None, "002", 2.25, dt.datetime(2026, 10, 28, 12, 13, 14, 123000)])
    sheet.append([None, "003", False, dt.time(12, 34, 56)])
    sheet.append([None, 'line,quote"\nUnicode café', None, "=1+2"])
    # Calamine trims these, whereas read-only openpyxl honors dimensions.
    sheet["F10"].number_format = "0.00"
    book.create_sheet("Another sheet").append(["ignored"])
    return book


@pytest.mark.parametrize("header_row", [None, 2])
def test_native_preserves_offsets_dates_text_and_dimensions(monkeypatch, header_row):
    source = io.BytesIO()
    _workbook().save(source)
    expected, old = _convert(source, "openpyxl", monkeypatch, header_row)
    actual, new = _convert(source, "calamine", monkeypatch, header_row)
    assert new[3] == "calamine"
    assert actual == expected
    assert new[:3] == old[:3]


def test_excel_error_cells_use_read_only_reader_instead_of_becoming_empty(monkeypatch):
    book = _workbook()
    book.active["C5"] = "#DIV/0!"
    source = io.BytesIO()
    book.save(source)
    expected, _ = _convert(source, "openpyxl", monkeypatch)
    actual, result = _convert(source, "calamine", monkeypatch)
    assert result[3] == "openpyxl"
    assert "#DIV/0!" in actual
    assert actual == expected


def test_partial_native_failure_restarts_without_duplicate_rows(monkeypatch):
    source = io.BytesIO()
    _workbook().save(source)
    expected, _ = _convert(source, "openpyxl", monkeypatch)
    original = excel._native_value
    calls = 0

    def fail_after_some_rows(value):
        nonlocal calls
        calls += 1
        if calls == 9:
            raise ValueError("Unsupported native value")
        return original(value)

    monkeypatch.setattr(excel, "_native_value", fail_after_some_rows)
    actual, result = _convert(source, "calamine", monkeypatch)
    assert result[3] == "openpyxl"
    assert actual == expected


def test_large_archive_uses_read_only_reader(monkeypatch):
    source = io.BytesIO()
    _workbook().save(source)
    monkeypatch.setattr(excel, "NATIVE_MAX_EXPANDED_BYTES", 1)
    _, result = _convert(source, "calamine", monkeypatch)
    assert result[3] == "openpyxl"
