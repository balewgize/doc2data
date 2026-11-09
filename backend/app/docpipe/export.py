"""CSV export.

E-commerce gets a Shopify product import file. Other verticals get a clean
generic CSV driven by their ``export_columns`` config.
"""

from __future__ import annotations

import csv
import html
import io
import re
from decimal import Decimal
from typing import Any

from app.docpipe.verticals import VerticalConfig

SHOPIFY_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags",
    "Published", "Option1 Name", "Option1 Value", "Option2 Name", "Option2 Value",
    "Option3 Name", "Option3 Value", "Variant SKU", "Variant Grams",
    "Variant Inventory Tracker", "Variant Inventory Qty", "Variant Inventory Policy",
    "Variant Fulfillment Service", "Variant Price", "Variant Compare At Price",
    "Variant Requires Shipping", "Variant Taxable", "Variant Barcode", "Image Src",
    "Image Position", "Image Alt Text", "Gift Card", "SEO Title", "SEO Description",
    "Google Shopping / Google Product Category", "Google Shopping / Gender",
    "Google Shopping / Age Group", "Google Shopping / MPN",
    "Google Shopping / Condition", "Google Shopping / Custom Product",
    "Variant Image", "Variant Weight Unit", "Variant Tax Code", "Cost per item",
    "Status",
]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (list, tuple)):
        return "; ".join(str(v) for v in value)
    return str(value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


def _shopify_rows(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        title = _text(record.get("title"))
        sku = _text(record.get("sku"))
        description = _text(record.get("description"))
        tags = record.get("tags") or []
        images = record.get("image_urls") or []
        first_image = images[0] if images else ""

        rows.append(
            {
                "Handle": _slug(sku or title),
                "Title": title,
                "Body (HTML)": f"<p>{html.escape(description)}</p>" if description else "",
                "Vendor": _text(record.get("vendor")),
                "Product Category": "",
                "Type": _text(record.get("product_type")),
                "Tags": ", ".join(tags) if isinstance(tags, list) else _text(tags),
                "Published": "FALSE",
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Option2 Name": "",
                "Option2 Value": "",
                "Option3 Name": "",
                "Option3 Value": "",
                "Variant SKU": sku,
                "Variant Grams": _text(record.get("weight_grams")) or "0",
                "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": "0",
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": _text(record.get("price")) or "0",
                "Variant Compare At Price": _text(record.get("compare_at_price")),
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Variant Barcode": "",
                "Image Src": _text(first_image),
                "Image Position": "1" if first_image else "",
                "Image Alt Text": title if first_image else "",
                "Gift Card": "FALSE",
                "SEO Title": _text(record.get("seo_title")) or title,
                "SEO Description": _text(record.get("seo_description")),
                "Google Shopping / Google Product Category": "",
                "Google Shopping / Gender": "",
                "Google Shopping / Age Group": "",
                "Google Shopping / MPN": "",
                "Google Shopping / Condition": "",
                "Google Shopping / Custom Product": "",
                "Variant Image": _text(first_image),
                "Variant Weight Unit": "g",
                "Variant Tax Code": "",
                "Cost per item": "",
                "Status": "draft",
            }
        )
    return rows


def export_csv(records: list[dict[str, Any]], config: VerticalConfig) -> str:
    buffer = io.StringIO()
    buffer.write("\ufeff")  # Excel-friendly UTF-8 BOM

    if config.id == "ecommerce":
        writer = csv.DictWriter(buffer, fieldnames=SHOPIFY_COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(_shopify_rows(records))
        return buffer.getvalue()

    headers = [header for header, _ in config.export_columns]
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    for record in records:
        writer.writerow([_text(record.get(field)) for _, field in config.export_columns])
    return buffer.getvalue()
