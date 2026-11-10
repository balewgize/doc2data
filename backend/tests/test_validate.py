from app.paperlane.validate import run_status, validate_records
from app.paperlane.verticals import ECOMMERCE, FINANCE


def test_missing_required_is_an_error():
    warnings = validate_records([{"sku": "P-1", "title": "Thing"}], ECOMMERCE)
    assert any(w.code == "missing_required" and w.severity == "error" for w in warnings)
    assert run_status([{"sku": "P-1"}], warnings) == "review"


def test_compare_at_below_price_warns():
    records = [{"sku": "P-1", "title": "Thing", "price": 20, "compare_at_price": 10}]
    warnings = validate_records(records, ECOMMERCE)
    assert any(w.code == "compare_at_below_price" for w in warnings)


def test_finance_total_mismatch_warns():
    records = [
        {
            "invoice_number": "INV-1",
            "vendor": "Acme",
            "subtotal": "100.00",
            "tax": "10.00",
            "total": "120.00",
        }
    ]
    warnings = validate_records(records, FINANCE)
    assert any(w.code == "total_mismatch" for w in warnings)


def test_clean_record_is_ok():
    records = [
        {
            "sku": "P-1",
            "title": "Thing",
            "description": "A thing",
            "price": 10,
            "currency": "USD",
            "image_urls": ["https://example.com/p.jpg"],
        }
    ]
    warnings = validate_records(records, ECOMMERCE)
    assert warnings == []
    assert run_status(records, warnings) == "ok"
