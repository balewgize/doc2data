"""Value normalization shared by every industry.

The LLM is asked for clean values, but real documents contain ``$1,299.00``,
``1,2 kg`` and ``10 x 5 x 2 cm``. Normalize before Pydantic validation so the
model can stay strict and the CSV stays importable.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil import parser as date_parser

from app.paperlane.verticals import FieldSpec, VerticalConfig

ISO_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR", "NGN",
    "BRL", "MXN", "ZAR", "KES", "ETB", "AED", "SAR", "SGD", "HKD", "NZD",
    "SEK", "NOK", "DKK", "PLN", "TRY", "KRW", "TWD", "THB", "IDR", "PHP",
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "₦": "NGN",
    "₺": "TRY",
    "₩": "KRW",
    "R$": "BRL",
}

WEIGHT_FACTORS = {
    "g": Decimal("1"),
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "kg": Decimal("1000"),
    "kgs": Decimal("1000"),
    "kilogram": Decimal("1000"),
    "kilograms": Decimal("1000"),
    "lb": Decimal("453.59237"),
    "lbs": Decimal("453.59237"),
    "pound": Decimal("453.59237"),
    "pounds": Decimal("453.59237"),
    "oz": Decimal("28.349523125"),
    "ounce": Decimal("28.349523125"),
    "ounces": Decimal("28.349523125"),
}

DIMENSION_FACTORS = {
    "mm": Decimal("0.1"),
    "cm": Decimal("1"),
    "m": Decimal("100"),
    "in": Decimal("2.54"),
    "inch": Decimal("2.54"),
    "inches": Decimal("2.54"),
    '"': Decimal("2.54"),
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def clean_vendor(value: Any) -> str | None:
    """Strip common invoice-address noise from a vendor name."""
    text = clean_text(value)
    if not text:
        return None
    text = re.sub(
        r"^(attn|attention|bill\s*to|invoice\s*from|from)\s*[:\-]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+(invoice|bill)$", "", text, flags=re.IGNORECASE)
    return text.strip() or None


def parse_date(value: Any) -> str | None:
    """Normalize common document dates to ISO 8601 (YYYY-MM-DD).

    Falls back to cleaned text when the date is ambiguous or unparseable, so a
    human can still review it instead of losing the value.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value).strip()
    try:
        return date_parser.parse(raw, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError, TypeError):
        return clean_text(raw)


def parse_decimal(value: Any) -> Decimal | None:
    """Parse money-like values from many locales and formats."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    raw = str(value).strip().replace("\u00a0", " ")
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    raw = re.sub(r"[A-Za-z$€£¥₹₦₺₩]", "", raw).replace(" ", "")

    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        tail = raw.rsplit(",", 1)[-1]
        raw = raw.replace(",", ".") if len(tail) == 2 else raw.replace(",", "")
    elif raw.count(".") > 1:
        head, _, tail = raw.rpartition(".")
        raw = head.replace(".", "") + "." + tail

    raw = re.sub(r"[^0-9.\-]", "", raw)
    if raw in ("", "-", ".", "-."):
        return None
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None
    return -parsed if negative else parsed


def parse_currency(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    upper = raw.upper()
    if upper in ISO_CURRENCIES:
        return upper
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in raw:
            return code
    # Handle "US Dollars", "euros", "GBP £", etc.
    words = {
        "DOLLAR": "USD", "DOLLARS": "USD", "USD": "USD",
        "EURO": "EUR", "EUROS": "EUR", "EUR": "EUR",
        "POUND": "GBP", "POUNDS": "GBP", "GBP": "GBP",
        "NAIRA": "NGN", "NGN": "NGN",
        "RUPEE": "INR", "RUPEES": "INR", "INR": "INR",
        "YEN": "JPY", "JPY": "JPY",
    }
    for word, code in words.items():
        if re.search(rf"\b{word}\b", upper):
            return code
    match = re.search(r"\b([A-Z]{3})\b", upper)
    return match.group(1) if match and match.group(1) in ISO_CURRENCIES else None


def parse_weight_grams(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return int(round(float(value)))

    raw = str(value).lower().strip()
    match = re.search(r"([\d.,]+)\s*([a-z\"]+)", raw)
    if match:
        amount = parse_decimal(match.group(1))
        unit = match.group(2)
        factor = WEIGHT_FACTORS.get(unit)
        if amount is not None and factor is not None:
            return int(round(float(amount * factor)))

    amount = parse_decimal(raw)
    return int(round(float(amount))) if amount is not None else None


def parse_weight_kg(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return round(float(value), 3)
    grams = parse_weight_grams(value)
    return round(grams / 1000, 3) if grams is not None else None


def parse_dimension_cm(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return round(float(value), 3)

    raw = str(value).lower().strip()
    match = re.search(r"([\d.,]+)\s*(mm|cm|m|inches|inch|in|\")", raw)
    if match:
        amount = parse_decimal(match.group(1))
        factor = DIMENSION_FACTORS.get(match.group(2))
        if amount is not None and factor is not None:
            return round(float(amount * factor), 3)

    amount = parse_decimal(raw)
    return round(float(amount), 3) if amount is not None else None


def parse_dimensions(value: Any) -> list[float] | None:
    """Turn ``10 x 5 x 2 cm`` into [10, 5, 2] in cm."""
    if value is None:
        return None
    raw = str(value).lower().strip()
    unit_match = re.search(r"(mm|cm|m|inches|inch|in|\")\s*$", raw)
    unit = unit_match.group(1) if unit_match else "cm"
    numbers = re.findall(r"[\d.,]+", raw)
    if len(numbers) < 3:
        return None
    values: list[float] = []
    for number in numbers[:3]:
        amount = parse_decimal(number)
        if amount is None:
            return None
        values.append(round(float(amount * DIMENSION_FACTORS.get(unit, Decimal("1"))), 3))
    return values


def _split_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in re.split(r"[,;|]", str(value)) if part.strip()]


def normalize_value(value: Any, field: FieldSpec) -> Any:
    if value is None or value == "":
        return None
    if field.type == "list_str":
        return _split_list(value)
    if field.type == "list_dict":
        return value if isinstance(value, list) else None
    if field.type == "int":
        if field.normalizer == "weight_grams":
            return parse_weight_grams(value)
        parsed = parse_decimal(value)
        return int(parsed) if parsed is not None else None
    if field.type == "float":
        if field.normalizer == "weight_kg":
            return parse_weight_kg(value)
        if field.normalizer == "dimension_cm":
            return parse_dimension_cm(value)
        parsed = parse_decimal(value)
        return float(parsed) if parsed is not None else None
    if field.type == "decimal":
        return parse_decimal(value)
    if field.normalizer == "price":
        return parse_decimal(value)
    if field.normalizer == "currency":
        return parse_currency(value)
    if field.normalizer == "weight_grams":
        return parse_weight_grams(value)
    if field.normalizer == "weight_kg":
        return parse_weight_kg(value)
    if field.normalizer == "dimension_cm":
        return parse_dimension_cm(value)
    if field.normalizer == "date":
        return parse_date(value)
    if field.normalizer == "vendor":
        return clean_vendor(value)
    return clean_text(value)


COMMON_ALIASES = {
    "product_name": "title",
    "name": "title",
    "brand": "vendor",
    "category": "product_type",
    "unit_price": "price",
    "list_price": "compare_at_price",
    "images": "image_urls",
    "image_urls": "image_urls",
    "invoice_no": "invoice_number",
    "invoice_id": "invoice_number",
    "shipment": "shipment_id",
    "bol_number": "shipment_id",
    "bill_of_lading_number": "shipment_id",
    "bl_number": "shipment_id",
    "tracking": "tracking_number",
    "tracking_no": "tracking_number",
    "pro_number": "tracking_number",
    "total_weight": "weight_kg",
    "gross_weight": "weight_kg",
    "package_count": "pieces",
    "no_of_pieces": "pieces",
    "ship_from": "origin",
    "ship_to": "destination",
    "total_amount": "total",
    "grand_total": "total",
    "claim_id": "claim_number",
}


def _key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def _canonical_key(key: str, config: VerticalConfig) -> str:
    """Map display labels and common aliases to the configured field name."""
    normalized = COMMON_ALIASES.get(_key(key), _key(key))
    if normalized in config.field_names:
        return normalized
    for field in config.fields:
        if normalized == _key(field.label):
            return field.name
    for name in config.field_names:
        if normalized.endswith("_" + name):
            return name
    return normalized


def normalize_record(raw: dict[str, Any], config: VerticalConfig) -> dict[str, Any]:
    """Map common aliases and normalize every configured field."""
    # Logistics models often put the BOL number in a separate key and use a
    # header label as shipment_id. Prefer the real BOL number when that happens.
    if config.id == "logistics":
        bol = next(
            (value for key, value in raw.items() if _key(key) in {"bol_number", "bill_of_lading_number", "bl_number"}),
            None,
        )
        current = next((value for key, value in raw.items() if _key(key) == "shipment_id"), None)
        if bol and (not current or any(word in str(current).lower() for word in ("cod", "amount", "lading"))):
            raw = {**raw, "shipment_id": bol}

    data: dict[str, Any] = {}
    for key, value in raw.items():
        data[_canonical_key(str(key), config)] = value

    # Expand a single dimensions string into the three fields when possible.
    if "dimensions" in data:
        dims = parse_dimensions(data.pop("dimensions"))
        if dims:
            for key, dim in zip(("length_cm", "width_cm", "height_cm"), dims):
                if key in config.field_names and data.get(key) is None:
                    data[key] = dim

    # One generic weight key can serve either vertical weight field.
    if "weight" in data:
        weight = data.pop("weight")
        if "weight_grams" in config.field_names and data.get("weight_grams") is None:
            data["weight_grams"] = weight
        elif "weight_kg" in config.field_names and data.get("weight_kg") is None:
            data["weight_kg"] = weight

    normalized: dict[str, Any] = {}
    for field in config.fields:
        if field.name in data:
            normalized[field.name] = normalize_value(data[field.name], field)

    # Preserve extra fields the model returned (useful for review, never exported).
    for key, value in data.items():
        if key not in normalized and value not in (None, ""):
            normalized[key] = value
    return normalized
