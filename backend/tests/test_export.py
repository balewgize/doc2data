import csv
import io

from app.doc2data.export import export_csv
from app.doc2data.verticals import ECOMMERCE, FINANCE


def test_shopify_export_has_expected_columns_and_values():
    csv_text = export_csv(
        [
            {
                "sku": "P-1001",
                "title": "Travel Press",
                "description": "Compact press",
                "vendor": "AeroPress",
                "product_type": "Coffee",
                "tags": ["coffee", "travel"],
                "price": "24.99",
                "compare_at_price": "29.99",
                "currency": "USD",
                "weight_grams": 1200,
                "image_urls": ["https://example.com/p.jpg"],
            }
        ],
        ECOMMERCE,
    )
    rows = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
    assert len(rows) == 1
    assert rows[0]["Handle"] == "p-1001"
    assert rows[0]["Title"] == "Travel Press"
    assert rows[0]["Variant SKU"] == "P-1001"
    assert rows[0]["Variant Price"] == "24.99"
    assert rows[0]["Variant Grams"] == "1200"
    assert rows[0]["Tags"] == "coffee, travel"
    assert rows[0]["Status"] == "draft"


def test_generic_finance_export():
    csv_text = export_csv(
        [{"invoice_number": "INV-1", "vendor": "Acme", "total": "120.00"}],
        FINANCE,
    )
    rows = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
    assert rows[0]["Invoice Number"] == "INV-1"
    assert rows[0]["Vendor"] == "Acme"
    assert rows[0]["Total"] == "120.00"
