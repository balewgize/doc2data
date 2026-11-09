from decimal import Decimal

import pytest

from app.docpipe.normalize import (
    normalize_record,
    parse_currency,
    parse_decimal,
    parse_dimensions,
    parse_weight_grams,
    parse_weight_kg,
)
from app.docpipe.verticals import ECOMMERCE, LOGISTICS


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$1,299.00", Decimal("1299.00")),
        ("€19,99", Decimal("19.99")),
        ("1.240,50", Decimal("1240.50")),
        ("1,240", Decimal("1240")),
        ("(42.50)", Decimal("-42.50")),
        (24.99, Decimal("24.99")),
    ],
)
def test_parse_decimal(raw, expected):
    assert parse_decimal(raw) == expected


def test_parse_decimal_rejects_empty():
    assert parse_decimal("") is None
    assert parse_decimal(None) is None
    assert parse_decimal("not a price") is None


@pytest.mark.parametrize(
    ("raw", "grams"),
    [
        ("1.2 kg", 1200),
        ("450 g", 450),
        ("1 lb", 454),
        ("12 oz", 340),
    ],
)
def test_parse_weight_grams(raw, grams):
    assert parse_weight_grams(raw) == grams


def test_parse_weight_kg():
    assert parse_weight_kg("12.5 kg") == 12.5
    assert parse_weight_kg(3.2) == 3.2


def test_parse_dimensions():
    assert parse_dimensions("10 x 5 x 2 cm") == [10.0, 5.0, 2.0]
    assert parse_dimensions("8 x 4 x 1 in") == [20.32, 10.16, 2.54]


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("USD", "USD"),
        ("€19,99", "EUR"),
        ("£ 10", "GBP"),
        ("Naira", "NGN"),
    ],
)
def test_parse_currency(raw, code):
    assert parse_currency(raw) == code


def test_normalize_record_expands_dimensions_and_weight():
    raw = {
        "SKU": "P-1",
        "Title": "Test",
        "Price": "$10.00",
        "Weight": "1.2 kg",
        "Dimensions": "10 x 5 x 2 cm",
        "Tags": "a, b, c",
    }
    record = normalize_record(raw, ECOMMERCE)
    assert record["price"] == Decimal("10.00")
    assert record["weight_grams"] == 1200
    assert record["length_cm"] == 10.0
    assert record["width_cm"] == 5.0
    assert record["height_cm"] == 2.0
    assert record["tags"] == ["a", "b", "c"]


def test_normalize_record_handles_logistics_weight():
    record = normalize_record({"Shipment ID": "S-1", "Weight": "12.5 kg"}, LOGISTICS)
    assert record["weight_kg"] == 12.5
