import csv
from pathlib import Path

from openpyxl import Workbook

from app.paperlane.extract import chunk_text, read_document

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "app" / "paperlane" / "sample_data"


def test_read_pdf_sample():
    text, meta = read_document(SAMPLE_DIR / "sample_supplier_catalog.pdf")
    assert "P-1001" in text
    assert meta["source_type"] == "pdf"
    assert meta["pages"] == 1


def test_read_csv_to_markdown_table(tmp_path):
    path = tmp_path / "products.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sku", "title", "price"])
        writer.writerow(["P-1", "Thing", "10.00"])
    text, meta = read_document(path)
    assert "| sku | title | price |" in text
    assert "| P-1 | Thing | 10.00 |" in text
    assert meta["source_type"] == "csv"


def test_read_xlsx_to_markdown_table(tmp_path):
    path = tmp_path / "products.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Catalog"
    sheet.append(["sku", "title", "price"])
    sheet.append(["P-1", "Thing", "10.00"])
    workbook.save(path)

    text, meta = read_document(path)
    assert "[sheet Catalog]" in text
    assert "| P-1 | Thing | 10.00 |" in text
    assert meta["source_type"] == "xlsx"


def test_chunk_text_splits_and_overlaps():
    text = "\n\n".join(f"Paragraph {i} " + ("x" * 80) for i in range(40))
    chunks = chunk_text(text, max_chars=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 600 for chunk in chunks)
    assert "Paragraph 0" in chunks[0]
