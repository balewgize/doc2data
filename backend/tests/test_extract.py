from decimal import Decimal
from pathlib import Path

from app.docpipe.extract import extract_document
from app.docpipe.verticals import ECOMMERCE, FINANCE, HEALTHCARE, LOGISTICS

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "app" / "docpipe" / "sample_data"


def test_ecommerce_sample_extracts_and_dedupes():
    result = extract_document(
        SAMPLE_DIR / ECOMMERCE.sample_file,
        ECOMMERCE.sample_file,
        ECOMMERCE,
    )
    assert len(result.records) == 3
    assert result.status == "review"
    assert any(w.code == "duplicate_record" for w in result.warnings)
    assert any(w.code == "missing_required" for w in result.warnings)

    by_sku = {record["sku"]: record for record in result.records}
    assert by_sku["P-1001"]["price"] == Decimal("24.99")
    assert by_sku["P-1002"]["price"] == Decimal("19.99")
    assert by_sku["P-1002"]["currency"] == "EUR"
    assert by_sku["P-1002"]["weight_grams"] == 450
    assert by_sku["P-1002"]["length_cm"] == 20.32


def test_finance_sample_detects_total_mismatch():
    result = extract_document(
        SAMPLE_DIR / FINANCE.sample_file,
        FINANCE.sample_file,
        FINANCE,
    )
    assert len(result.records) == 3
    assert any(w.code == "total_mismatch" for w in result.warnings)


def test_logistics_sample():
    result = extract_document(
        SAMPLE_DIR / LOGISTICS.sample_file,
        LOGISTICS.sample_file,
        LOGISTICS,
    )
    assert len(result.records) == 2
    assert result.records[0]["weight_kg"] == 12.5
    assert result.records[1]["weight_kg"] == 1240.0


def test_healthcare_sample_flags_allowed_above_billed():
    result = extract_document(
        SAMPLE_DIR / HEALTHCARE.sample_file,
        HEALTHCARE.sample_file,
        HEALTHCARE,
    )
    assert len(result.records) == 2
    assert any(w.code == "allowed_above_billed" for w in result.warnings)
