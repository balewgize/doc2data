"""Industry configurations for the shared extraction engine.

Adding an industry is intentionally a data change, not a rewrite: define the
fields, the extraction prompt, the dedupe key and the CSV columns. The core
pipeline handles reading, chunking, LLM calls, normalization, validation,
storage and export.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import ConfigDict, Field, create_model

FieldType = Literal["str", "decimal", "int", "float", "list_str", "list_dict"]
Normalizer = Literal[
    "text",
    "price",
    "currency",
    "weight_grams",
    "weight_kg",
    "dimension_cm",
    "date",
    "vendor",
]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    type: FieldType = "str"
    required: bool = False
    recommended: bool = False
    description: str = ""
    normalizer: Normalizer | None = None


@dataclass(frozen=True)
class VerticalConfig:
    id: str
    label: str
    description: str
    record_noun: str
    fields: tuple[FieldSpec, ...]
    dedupe_key: str
    system_prompt: str
    export_columns: tuple[tuple[str, str], ...]
    sample_file: str
    real_sample_file: str | None = None
    ready: bool = True

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    def field(self, name: str) -> FieldSpec | None:
        return next((f for f in self.fields if f.name == name), None)


BASE_TYPES: dict[str, Any] = {
    "str": str,
    "decimal": Decimal,
    "int": int,
    "float": float,
    "list_str": list[str],
    "list_dict": list[dict[str, Any]],
}

_record_models: dict[str, type] = {}


def build_record_model(config: VerticalConfig, lenient: bool = False) -> type:
    """Create a validated Pydantic model from a vertical's field list.

    ``lenient=True`` makes every field optional so a record with missing data
    can still reach human review instead of being dropped by the parser. The
    strict model is used only to build the JSON schema shown to the LLM.
    """
    cache_key = f"{config.id}:{lenient}"
    if cache_key in _record_models:
        return _record_models[cache_key]

    declarations: dict[str, Any] = {}
    for f in config.fields:
        base = BASE_TYPES[f.type]
        if f.type in ("list_str", "list_dict"):
            declarations[f.name] = (
                base,
                Field(default_factory=list, description=f.description),
            )
        elif f.required and not lenient:
            declarations[f.name] = (base, Field(..., description=f.description))
        else:
            declarations[f.name] = (
                base | None,
                Field(default=None, description=f.description),
            )

    model = create_model(
        f"{config.id.title()}{'Lenient' if lenient else 'Record'}",
        __config__=ConfigDict(extra="allow"),
        **declarations,
    )
    _record_models[cache_key] = model
    return model


ECOMMERCE = VerticalConfig(
    id="ecommerce",
    label="E-commerce catalog",
    description="Supplier PDFs, spreadsheets and text -> clean product records and a Shopify import CSV.",
    record_noun="product",
    dedupe_key="sku",
    sample_file="sample_supplier_catalog.pdf",
    real_sample_file="sample_catalog_public.csv",
    fields=(
        FieldSpec("sku", "SKU", required=True, description="Supplier or internal SKU.", normalizer="text"),
        FieldSpec("title", "Title", required=True, description="Product name.", normalizer="text"),
        FieldSpec("description", "Description", recommended=True, description="Selling description."),
        FieldSpec("vendor", "Vendor", description="Brand or supplier.", normalizer="vendor"),
        FieldSpec("product_type", "Product type", description="Category or product type."),
        FieldSpec("tags", "Tags", type="list_str", description="Search/category tags."),
        FieldSpec("price", "Price", type="decimal", required=True, description="Selling price.", normalizer="price"),
        FieldSpec("compare_at_price", "Compare-at price", type="decimal", description="Original/list price.", normalizer="price"),
        FieldSpec("currency", "Currency", recommended=True, description="ISO 4217 currency code.", normalizer="currency"),
        FieldSpec("weight_grams", "Weight (g)", type="int", description="Shipping weight in grams.", normalizer="weight_grams"),
        FieldSpec("length_cm", "Length (cm)", type="float", description="Package length in cm.", normalizer="dimension_cm"),
        FieldSpec("width_cm", "Width (cm)", type="float", description="Package width in cm.", normalizer="dimension_cm"),
        FieldSpec("height_cm", "Height (cm)", type="float", description="Package height in cm.", normalizer="dimension_cm"),
        FieldSpec("image_urls", "Image URLs", type="list_str", recommended=True, description="Product image URLs."),
        FieldSpec("seo_title", "SEO title", description="Search title."),
        FieldSpec("seo_description", "SEO description", description="Search description."),
    ),
    system_prompt=(
        "You extract product catalog records from supplier documents. "
        "Return one record per sellable product/SKU. Do not invent specifications. "
        "If a value is missing, use null. Keep descriptions factual and concise."
    ),
    export_columns=(
        ("SKU", "sku"),
        ("Title", "title"),
        ("Vendor", "vendor"),
        ("Type", "product_type"),
        ("Price", "price"),
        ("Currency", "currency"),
        ("Weight (g)", "weight_grams"),
        ("Tags", "tags"),
        ("Description", "description"),
    ),
)

FINANCE = VerticalConfig(
    id="finance",
    label="Finance documents",
    description="Invoices and bills -> validated invoice records with totals and line items.",
    record_noun="invoice",
    dedupe_key="invoice_number",
    sample_file="sample_invoice.txt",
    real_sample_file="sample_invoice_public.pdf",
    fields=(
        FieldSpec("invoice_number", "Invoice number", required=True, description="Vendor invoice number.", normalizer="text"),
        FieldSpec("vendor", "Vendor", required=True, description="Supplier / payee.", normalizer="vendor"),
        FieldSpec("invoice_date", "Invoice date", description="Issue date, ISO 8601.", normalizer="date"),
        FieldSpec("due_date", "Due date", description="Payment due date, ISO 8601.", normalizer="date"),
        FieldSpec("currency", "Currency", recommended=True, description="ISO 4217 currency code.", normalizer="currency"),
        FieldSpec("subtotal", "Subtotal", type="decimal", description="Amount before tax.", normalizer="price"),
        FieldSpec("tax", "Tax", type="decimal", description="Tax amount.", normalizer="price"),
        FieldSpec("total", "Total", type="decimal", required=True, description="Invoice total.", normalizer="price"),
        FieldSpec("po_number", "PO number", description="Purchase order reference."),
        FieldSpec("payment_terms", "Payment terms", description="e.g. Net 30."),
        FieldSpec("line_items", "Line items", type="list_str", description="Short line item descriptions."),
    ),
    system_prompt=(
        "You extract vendor invoices. Return one record per invoice. "
        "Vendor means the organization issuing the invoice (for example "
        "'Amazon Web Services'), not the bill-to customer, an attention line, "
        "or the document title. Use ISO 8601 dates. Amounts must be numbers, "
        "not formatted strings. Do not invent tax, totals, or line items. "
        "If a value is absent, use null."
    ),
    export_columns=(
        ("Invoice Number", "invoice_number"),
        ("Vendor", "vendor"),
        ("Invoice Date", "invoice_date"),
        ("Due Date", "due_date"),
        ("Currency", "currency"),
        ("Subtotal", "subtotal"),
        ("Tax", "tax"),
        ("Total", "total"),
        ("PO Number", "po_number"),
        ("Payment Terms", "payment_terms"),
        ("Line Items", "line_items"),
    ),
)

LOGISTICS = VerticalConfig(
    id="logistics",
    label="Logistics documents",
    description="Shipment confirmations and packing lists -> structured consignment records.",
    record_noun="shipment",
    dedupe_key="shipment_id",
    sample_file="sample_shipment.txt",
    real_sample_file="sample_bol_public.pdf",
    fields=(
        FieldSpec("shipment_id", "Shipment ID", required=True, description="Carrier or internal shipment ID.", normalizer="text"),
        FieldSpec("carrier", "Carrier", description="Carrier name."),
        FieldSpec("tracking_number", "Tracking number", description="Carrier tracking reference."),
        FieldSpec("origin", "Origin", description="Origin city/country."),
        FieldSpec("destination", "Destination", description="Destination city/country."),
        FieldSpec("ship_date", "Ship date", description="ISO 8601 date.", normalizer="date"),
        FieldSpec("delivery_date", "Delivery date", description="ISO 8601 date.", normalizer="date"),
        FieldSpec("weight_kg", "Weight (kg)", type="float", description="Gross weight in kg.", normalizer="weight_kg"),
        FieldSpec("pieces", "Pieces", type="int", description="Number of packages."),
        FieldSpec("incoterm", "Incoterm", description="e.g. DAP, FOB."),
        FieldSpec("service", "Service", description="Service level."),
    ),
    system_prompt=(
        "You extract shipment records from bills of lading, packing lists and shipment confirmations. "
        "Return exactly one record per shipment; do not create multiple records for the same BOL. "
        "Mapping rules: shipment_id is the Bill of Lading Number / BOL number / shipment ID, "
        "never a label such as 'COD Amount'. carrier is the transporter (for example "
        "'Southeastern Freight Lines'), not the shipper or consignee. tracking_number is the "
        "PRO number, tracking number or carrier reference. origin is the SHIP FROM location; "
        "destination is the SHIP TO location. weight_kg is the total gross weight converted "
        "to kilograms (1 lb = 0.453592 kg; for example, 1,240 lb = 562.45 kg). "
        "pieces is the total package count. Use ISO 8601 dates. Do not invent values."
    ),
    export_columns=(
        ("Shipment ID", "shipment_id"),
        ("Carrier", "carrier"),
        ("Tracking Number", "tracking_number"),
        ("Origin", "origin"),
        ("Destination", "destination"),
        ("Ship Date", "ship_date"),
        ("Delivery Date", "delivery_date"),
        ("Weight (kg)", "weight_kg"),
        ("Pieces", "pieces"),
        ("Incoterm", "incoterm"),
        ("Service", "service"),
    ),
)

HEALTHCARE = VerticalConfig(
    id="healthcare",
    label="Healthcare claims",
    description="Administrative claim/EOB documents -> claim-line records. Not clinical advice.",
    record_noun="claim line",
    dedupe_key="claim_number",
    sample_file="sample_claim.txt",
    real_sample_file="sample_claim_public.pdf",
    fields=(
        FieldSpec("claim_number", "Claim number", required=True, description="Payer claim reference.", normalizer="text"),
        FieldSpec("payer", "Payer", description="Insurance payer."),
        FieldSpec("provider", "Provider", description="Billing provider."),
        FieldSpec("service_date", "Service date", description="ISO 8601 date.", normalizer="date"),
        FieldSpec("member_id", "Member ID", description="Member identifier (no patient names).", normalizer="text"),
        FieldSpec("diagnosis_codes", "Diagnosis codes", type="list_str", description="ICD codes as printed."),
        FieldSpec("procedure_codes", "Procedure codes", type="list_str", description="CPT/HCPCS codes as printed."),
        FieldSpec("billed_amount", "Billed amount", type="decimal", description="Billed amount.", normalizer="price"),
        FieldSpec("allowed_amount", "Allowed amount", type="decimal", description="Allowed amount.", normalizer="price"),
        FieldSpec("patient_responsibility", "Patient responsibility", type="decimal", description="Patient responsibility.", normalizer="price"),
    ),
    system_prompt=(
        "You extract administrative healthcare claim or EOB data. Return one record per claim line. "
        "This is administrative data extraction, not medical advice. Do not infer diagnoses or invent codes. "
        "Never extract patient names; use the member ID only. If a value is absent, use null."
    ),
    export_columns=(
        ("Claim Number", "claim_number"),
        ("Payer", "payer"),
        ("Provider", "provider"),
        ("Service Date", "service_date"),
        ("Member ID", "member_id"),
        ("Diagnosis Codes", "diagnosis_codes"),
        ("Procedure Codes", "procedure_codes"),
        ("Billed", "billed_amount"),
        ("Allowed", "allowed_amount"),
        ("Patient Responsibility", "patient_responsibility"),
    ),
)

VERTICALS: dict[str, VerticalConfig] = {
    c.id: c for c in (ECOMMERCE, FINANCE, LOGISTICS, HEALTHCARE)
}
