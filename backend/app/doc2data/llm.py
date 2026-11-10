"""LLM providers.

Three implementations share one interface so the rest of the pipeline never
knows whether extraction runs on OpenRouter, a local Ollama model, or the
deterministic mock used for tests and offline demos.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

from app.core.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    resolved_provider,
)
from app.doc2data.normalize import parse_dimensions
from app.doc2data.verticals import VerticalConfig, build_record_model


class ProviderError(RuntimeError):
    """Raised when the configured provider cannot run."""


class ExtractionProvider(Protocol):
    name: str

    def extract(self, text: str, config: VerticalConfig) -> dict[str, Any]: ...


def _field_instructions(config: VerticalConfig) -> str:
    lines = []
    for f in config.fields:
        flags = []
        if f.required:
            flags.append("required")
        if f.recommended:
            flags.append("recommended")
        suffix = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"- {f.name} [{f.type}]{suffix}: {f.description or f.label}")
    return "\n".join(lines)


def build_system_prompt(config: VerticalConfig) -> str:
    schema = json.dumps(build_record_model(config).model_json_schema(), indent=2)
    return f"""{config.system_prompt}

You are a document data extraction engine. Return ONLY a JSON object with a
"records" array. One object per {config.record_noun}.

Rules:
- Use exactly the field names listed below.
- Use null when a value is genuinely absent. Never guess or invent data.
- Numbers must be JSON numbers, not formatted strings.
- Lists must be JSON arrays of strings.
- Normalize currency values to ISO 4217 codes.
- If the document contains no matching records, return {{"records": []}}.

Fields:
{_field_instructions(config)}

JSON Schema:
{schema}
"""


def _clean_json_content(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    # Fallback for models that wrap JSON in prose.
    if not content.startswith(("{", "[")):
        match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
        if match:
            content = match.group(1)
    return content


def _normalize_provider_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"records": payload}
    if isinstance(payload, dict):
        records = payload.get("records")
        if records is None and any(k in payload for k in ("sku", "invoice_number", "shipment_id", "claim_number")):
            return {"records": [payload]}
        if isinstance(records, list):
            return {"records": records}
    return {"records": []}


class OpenAICompatibleProvider:
    """Works with OpenRouter, Ollama and any OpenAI-compatible server."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        json_mode: bool = True,
        default_headers: dict[str, str] | None = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is in pyproject
            raise ProviderError("The openai package is not installed.") from exc

        self.name = name
        self.model = model
        self.json_mode = json_mode
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=90,
            default_headers=default_headers,
        )

    def extract(self, text: str, config: VerticalConfig) -> dict[str, Any]:
        system = build_system_prompt(config)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Extract the records from this document chunk:\n\n{text}"},
            ],
        }
        if self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ProviderError(f"{self.name} extraction failed: {exc}") from exc

        content = response.choices[0].message.content or ""
        try:
            payload = json.loads(_clean_json_content(content))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"{self.name} returned invalid JSON: {exc}") from exc
        return _normalize_provider_payload(payload)


class MockProvider:
    """Deterministic key/value parser used for tests and offline demos.

    It understands the bundled sample documents, not arbitrary PDFs. Real
    extraction uses OpenAI or Ollama.
    """

    name = "mock"

    def extract(self, text: str, config: VerticalConfig) -> dict[str, Any]:
        blocks = [b.strip() for b in re.split(r"\n\s*---\s*\n", text) if b.strip()]
        if not blocks:
            return {"records": []}

        records: list[dict[str, Any]] = []
        for block in blocks:
            record = self._parse_block(block, config)
            if record:
                records.append(record)
        return {"records": records}

    @staticmethod
    def _key_to_field(key: str, config: VerticalConfig) -> str | None:
        normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        aliases = {
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
            "tracking": "tracking_number",
            "total_amount": "total",
            "grand_total": "total",
            "claim_id": "claim_number",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in config.field_names:
            return normalized
        for field in config.field_names:
            if normalized.endswith("_" + field):
                return field
        return None

    def _parse_block(self, block: str, config: VerticalConfig) -> dict[str, Any]:
        record: dict[str, Any] = {}
        current_key: str | None = None
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("[page", "#")):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                current_key = key.strip()
                value = value.strip()
                if value:
                    record[current_key] = value
                else:
                    record[current_key] = ""
            elif current_key:
                record[current_key] = f"{record.get(current_key, '')} {line}".strip()

        mapped: dict[str, Any] = {}
        for key, value in record.items():
            field_name = self._key_to_field(key, config)
            if field_name:
                mapped[field_name] = value
            elif key.lower().strip() == "dimensions":
                dims = parse_dimensions(value)
                if dims:
                    for name, dim in zip(("length_cm", "width_cm", "height_cm"), dims):
                        if name in config.field_names:
                            mapped[name] = dim
            elif key.lower().strip() == "weight":
                if "weight_grams" in config.field_names:
                    mapped["weight_grams"] = value
                elif "weight_kg" in config.field_names:
                    mapped["weight_kg"] = value
        return mapped


def get_provider() -> ExtractionProvider:
    provider = resolved_provider()
    if provider == "mock":
        return MockProvider()
    if provider == "openrouter":
        if not OPENROUTER_API_KEY:
            raise ProviderError(
                "LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set."
            )
        return OpenAICompatibleProvider(
            name="openrouter",
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            json_mode=False,
            default_headers={
                "HTTP-Referer": "https://github.com/balewgize/doc2data",
                "X-Title": "Doc2Data",
            },
        )
    if provider == "ollama":
        return OpenAICompatibleProvider(
            name="ollama",
            model=OLLAMA_MODEL,
            api_key="ollama",
            base_url=OLLAMA_BASE_URL,
            json_mode=False,
        )
    raise ProviderError(
        f"Unknown LLM_PROVIDER={provider!r}. Use mock, openrouter or ollama."
    )
