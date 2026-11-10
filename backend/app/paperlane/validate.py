"""Business validation for extracted records.

Validation never blocks the run. It returns typed warnings/errors so a human
can review before exporting, which is how document workflows actually operate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.paperlane.models import WarningItem
from app.paperlane.verticals import VerticalConfig


def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _record_key(record: dict[str, Any], config: VerticalConfig) -> str:
    return str(record.get(config.dedupe_key) or "unknown")


def validate_records(records: list[dict[str, Any]], config: VerticalConfig) -> list[WarningItem]:
    warnings: list[WarningItem] = []

    for record in records:
        key = _record_key(record, config)

        for field in config.fields:
            value = record.get(field.name)
            if field.required and _blank(value):
                warnings.append(
                    WarningItem(
                        code="missing_required",
                        message=f"{field.label} is required but missing.",
                        severity="error",
                        record_key=key,
                    )
                )
            elif field.recommended and _blank(value):
                warnings.append(
                    WarningItem(
                        code="missing_recommended",
                        message=f"{field.label} is missing. Add it before publishing.",
                        severity="warning",
                        record_key=key,
                    )
                )

            if field.type in ("decimal", "int", "float") and value is not None:
                number = _decimal(value)
                if number is not None and number < 0:
                    severity = "error" if field.type == "decimal" and "price" in field.name else "warning"
                    warnings.append(
                        WarningItem(
                            code="negative_value",
                            message=f"{field.label} is negative ({value}).",
                            severity=severity,
                            record_key=key,
                        )
                    )

        currency = record.get("currency")
        if currency and (not isinstance(currency, str) or len(currency) != 3):
            warnings.append(
                WarningItem(
                    code="invalid_currency",
                    message=f"Currency {currency!r} is not a 3-letter ISO code.",
                    severity="warning",
                    record_key=key,
                )
            )

        if config.id == "ecommerce":
            price = _decimal(record.get("price"))
            compare_at = _decimal(record.get("compare_at_price"))
            if price is not None and compare_at is not None and compare_at < price:
                warnings.append(
                    WarningItem(
                        code="compare_at_below_price",
                        message="Compare-at price is lower than the selling price.",
                        severity="warning",
                        record_key=key,
                    )
                )

        elif config.id == "finance":
            subtotal = _decimal(record.get("subtotal"))
            tax = _decimal(record.get("tax"))
            total = _decimal(record.get("total"))
            if subtotal is not None and tax is not None and total is not None:
                if abs(total - (subtotal + tax)) > Decimal("0.02"):
                    warnings.append(
                        WarningItem(
                            code="total_mismatch",
                            message=f"Total {total} does not equal subtotal {subtotal} + tax {tax}.",
                            severity="warning",
                            record_key=key,
                        )
                    )

        elif config.id == "logistics":
            weight = _decimal(record.get("weight_kg"))
            pieces = _decimal(record.get("pieces"))
            if weight is not None and weight <= 0:
                warnings.append(
                    WarningItem(
                        code="invalid_weight",
                        message="Shipment weight must be greater than zero.",
                        severity="warning",
                        record_key=key,
                    )
                )
            if pieces is not None and pieces <= 0:
                warnings.append(
                    WarningItem(
                        code="invalid_pieces",
                        message="Piece count must be greater than zero.",
                        severity="warning",
                        record_key=key,
                    )
                )

        elif config.id == "healthcare":
            billed = _decimal(record.get("billed_amount"))
            allowed = _decimal(record.get("allowed_amount"))
            patient = _decimal(record.get("patient_responsibility"))
            if billed is not None and allowed is not None and allowed > billed:
                warnings.append(
                    WarningItem(
                        code="allowed_above_billed",
                        message="Allowed amount is higher than the billed amount.",
                        severity="warning",
                        record_key=key,
                    )
                )
            if allowed is not None and patient is not None and patient > allowed:
                warnings.append(
                    WarningItem(
                        code="patient_above_allowed",
                        message="Patient responsibility is higher than the allowed amount.",
                        severity="warning",
                        record_key=key,
                    )
                )

    return warnings


def run_status(records: list[dict[str, Any]], warnings: list[WarningItem]) -> str:
    if not records:
        return "error"
    if any(w.severity == "error" for w in warnings):
        return "review"
    if warnings:
        return "review"
    return "ok"
