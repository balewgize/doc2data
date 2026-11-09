"""The extraction pipeline: read -> chunk -> LLM -> normalize -> validate."""

from __future__ import annotations

import csv
import io
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.config import MAX_CHARS_PER_CHUNK
from app.docpipe.llm import ProviderError, get_provider
from app.docpipe.models import WarningItem
from app.docpipe.normalize import normalize_record
from app.docpipe.validate import run_status, validate_records
from app.docpipe.verticals import VerticalConfig, build_record_model


class UnsupportedDocument(ValueError):
    """Raised for a file type we cannot read yet."""


class ExtractionError(RuntimeError):
    """Raised when the document could not be processed at all."""


@dataclass
class ExtractionResult:
    records: list[dict[str, Any]]
    warnings: list[WarningItem] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        return run_status(self.records, self.warnings)


def read_document(path: Path) -> tuple[str, dict[str, Any]]:
    suffix = path.suffix.lower()
    meta: dict[str, Any] = {"source_type": suffix.lstrip(".") or "unknown", "pages": None}

    if suffix == ".pdf":
        try:
            import pymupdf
        except ImportError as exc:  # pragma: no cover
            raise UnsupportedDocument("PDF support requires pymupdf.") from exc
        with pymupdf.open(path) as doc:
            pages = []
            for index, page in enumerate(doc, start=1):
                pages.append(f"[page {index}]\n{page.get_text()}")
            meta["pages"] = len(doc)
            text = "\n\n".join(pages)
        return text, meta

    if suffix in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:  # pragma: no cover
            raise UnsupportedDocument("Excel support requires openpyxl.") from exc
        workbook = load_workbook(path, data_only=True, read_only=True)
        sections = []
        for sheet in workbook.worksheets:
            rows = []
            for row in sheet.iter_rows(values_only=True):
                values = ["" if cell is None else str(cell) for cell in row]
                if any(values):
                    rows.append(values)
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                header = rows[0]
                body = rows[1:]
                table = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
                table += ["| " + " | ".join(r) + " |" for r in body]
                sections.append(f"[sheet {sheet.title}]\n" + "\n".join(table))
        meta["pages"] = len(workbook.worksheets)
        return "\n\n".join(sections), meta

    if suffix == ".csv":
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        rows = list(csv.reader(io.StringIO(raw)))
        if not rows:
            return "", meta
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        header, body = rows[0], rows[1:]
        table = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
        table += ["| " + " | ".join(r) + " |" for r in body]
        return "\n".join(table), meta

    if suffix in (".txt", ".md", ".json"):
        return path.read_text(encoding="utf-8", errors="replace"), meta

    if suffix == ".xls":
        raise UnsupportedDocument("Legacy .xls is not supported. Save the file as .xlsx first.")

    raise UnsupportedDocument(f"Unsupported file type: {suffix or 'unknown'}")


def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK, overlap: int = 400) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(paragraph), max_chars - overlap):
                chunks.append(paragraph[start : start + max_chars])
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)

    if overlap and len(chunks) > 1:
        with_overlap = [chunks[0]]
        for previous, chunk in zip(chunks, chunks[1:]):
            with_overlap.append((previous[-overlap:] + "\n\n" + chunk).strip())
        chunks = with_overlap
    return chunks


def extract_document(path: Path, filename: str, config: VerticalConfig) -> ExtractionResult:
    started = time.perf_counter()
    text, read_meta = read_document(path)
    source_chars = len(text)
    if not text.strip():
        raise ExtractionError("The document contains no readable text. Scanned PDFs need OCR first.")

    chunks = chunk_text(text)
    provider = get_provider()
    model = build_record_model(config, lenient=True)
    records: list[dict[str, Any]] = []
    warnings: list[WarningItem] = []
    seen: set[str] = set()

    for index, chunk in enumerate(chunks, start=1):
        try:
            payload = provider.extract(chunk, config)
        except ProviderError as exc:
            warnings.append(
                WarningItem(
                    code="chunk_failed",
                    message=f"Chunk {index}/{len(chunks)} failed: {exc}",
                    severity="error",
                )
            )
            continue

        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list):
            warnings.append(
                WarningItem(
                    code="invalid_payload",
                    message=f"Chunk {index}/{len(chunks)} returned records that were not a list.",
                    severity="error",
                )
            )
            continue

        for raw in raw_records:
            if not isinstance(raw, dict):
                continue
            normalized = normalize_record(raw, config)
            try:
                validated = model.model_validate(normalized).model_dump()
            except ValidationError as exc:
                warnings.append(
                    WarningItem(
                        code="invalid_record",
                        message=f"Record failed schema validation: {exc.errors()[0].get('msg', 'invalid value')}",
                        severity="error",
                        record_key=str(normalized.get(config.dedupe_key) or "unknown"),
                    )
                )
                validated = normalized

            key_value = validated.get(config.dedupe_key)
            key = str(key_value).strip().lower() if key_value not in (None, "") else ""
            if key:
                if key in seen:
                    warnings.append(
                        WarningItem(
                            code="duplicate_record",
                            message=f"Duplicate {config.dedupe_key} {key_value!r}; later record ignored.",
                            severity="warning",
                            record_key=str(key_value),
                        )
                    )
                    continue
                seen.add(key)
            records.append(validated)

    warnings.extend(validate_records(records, config))
    if not records and not any(w.severity == "error" for w in warnings):
        warnings.append(
            WarningItem(
                code="no_records",
                message="No matching records were found in this document.",
                severity="error",
            )
        )

    return ExtractionResult(
        records=records,
        warnings=warnings,
        meta={
            "filename": filename,
            "provider": provider.name,
            "source_type": read_meta.get("source_type"),
            "pages": read_meta.get("pages"),
            "source_chars": source_chars,
            "chunks": len(chunks),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        },
    )
