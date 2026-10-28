"""Run inside the Linux image to verify the native wheel and default reader."""
import io
import tempfile
from pathlib import Path

from openpyxl import Workbook
from app.services import parser

book = Workbook(write_only=True)
sheet = book.create_sheet()
sheet.append(["code", "value"])
sheet.append(["001", 1])
sheet.append(["002", None])
source = io.BytesIO()
book.save(source)
with tempfile.TemporaryDirectory() as directory:
    parser.DATA_DIR = Path(directory)
    parser.SMALL_FILE_THRESHOLD = 1
    result = parser.parse_upload("native-smoke.xlsx", source, source.tell())
    assert result["shape"] == {"rows": 2, "columns": 2}
    assert result["profile"]["reader"] == "calamine", result["profile"]
    assert result["schema"][1]["null_count"] == 1
    assert result["_data_path"].read_text().splitlines()[-1] == "002,"
print("Linux image native Excel ingestion passed")
