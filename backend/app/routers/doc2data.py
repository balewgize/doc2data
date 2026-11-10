"""Doc2Data API routes."""

from __future__ import annotations

import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import (
    DATABASE_PATH,
    MAX_UPLOAD_MB,
    OLLAMA_MODEL,
    OPENAI_MODEL,
    resolved_provider,
)
from app.doc2data.export import export_csv
from app.doc2data.extract import (
    ExtractionError,
    ExtractionResult,
    UnsupportedDocument,
    extract_document,
)
from app.doc2data.llm import ProviderError
from app.doc2data.models import Column, Run
from app.doc2data.normalize import normalize_record, normalize_value
from app.doc2data.storage import get_run, list_runs, save_run
from app.doc2data.validate import refresh_warnings, run_status, validate_records
from app.doc2data.verticals import VERTICALS

router = APIRouter(prefix="/api/doc2data", tags=["doc2data"])

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xlsm", ".csv", ".txt", ".md", ".json"}
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "doc2data" / "sample_data"
REAL_RESULTS_DIR = SAMPLE_DIR / "real_results"


class RecordEdit(BaseModel):
    field: str = Field(min_length=1)
    value: Any = None


def _config(vertical: str):
    config = VERTICALS.get(vertical)
    if config is None:
        raise HTTPException(status_code=400, detail=f"Unknown vertical {vertical!r}.")
    return config


def _columns(config) -> list[Column]:
    return [Column(key=f.name, label=f.label, type=f.type) for f in config.fields]


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_result(result: ExtractionResult, filename: str, config) -> Run:
    run = Run(
        id=_new_run_id(),
        created_at=_now(),
        vertical=config.id,
        vertical_label=config.label,
        filename=filename,
        provider=str(result.meta.get("provider", resolved_provider())),
        status=result.status,
        records=result.records,
        warnings=result.warnings,
        columns=_columns(config),
        meta=result.meta,
    )
    save_run(run)
    return run


def _run_document(path: Path, filename: str, vertical: str) -> Run:
    config = _config(vertical)
    try:
        result = extract_document(path, filename, config)
    except UnsupportedDocument as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _save_result(result, filename, config)


def _bundled_real_sample(config) -> Run:
    """Serve a recorded extraction when no LLM provider is configured.

    The public samples are fixed files, so the portfolio demo can show the
    review workflow without an API key. Configure OpenAI or Ollama to run them
    live instead.
    """
    fixture_path = REAL_RESULTS_DIR / f"{config.id}.json"
    if not fixture_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Bundled result missing for {config.label}.",
        )

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    records = [normalize_record(record, config) for record in payload.get("records", [])]
    result = ExtractionResult(
        records=records,
        warnings=validate_records(records, config),
        meta={
            "filename": config.real_sample_file,
            "provider": "demo",
            "source_type": "bundled",
            "pages": payload.get("pages"),
            "source_chars": payload.get("source_chars", 0),
            "chunks": payload.get("chunks", 1),
            "elapsed_ms": 0,
            "recorded_with": payload.get("recorded_with"),
            "public_sample": True,
        },
    )
    return _save_result(result, config.real_sample_file or fixture_path.name, config)


@router.get("/verticals")
def verticals() -> list[dict[str, object]]:
    return [
        {
            "id": config.id,
            "label": config.label,
            "description": config.description,
            "ready": config.ready,
            "real_sample": bool(config.real_sample_file),
            "fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "type": f.type,
                    "required": f.required,
                    "recommended": f.recommended,
                }
                for f in config.fields
            ],
        }
        for config in VERTICALS.values()
    ]


@router.get("/health")
def health() -> dict[str, object]:
    provider = resolved_provider()
    model = (
        OLLAMA_MODEL
        if provider == "ollama"
        else OPENAI_MODEL
        if provider == "openai"
        else "mock"
    )
    return {
        "status": "ok",
        "provider": provider,
        "model": model,
        "verticals": list(VERTICALS),
        "database": str(DATABASE_PATH),
        "max_upload_mb": MAX_UPLOAD_MB,
    }


@router.post("/extract", response_model=Run)
async def extract(
    file: UploadFile = File(...),
    vertical: str = Form("ecommerce"),
) -> Run:
    config = _config(vertical)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {suffix or 'unknown'}. Use PDF, XLSX, CSV, TXT, MD or JSON.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {MAX_UPLOAD_MB} MB.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        return _run_document(temp_path, file.filename or f"upload{suffix}", config.id)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.post("/extract/sample", response_model=Run)
def extract_sample(vertical: str = "ecommerce", real: bool = False) -> Run:
    config = _config(vertical)
    if real:
        if not config.real_sample_file:
            raise HTTPException(
                status_code=400,
                detail=f"No real sample is bundled for {config.label}.",
            )
        if resolved_provider() == "mock":
            return _bundled_real_sample(config)
        sample = SAMPLE_DIR / config.real_sample_file
    else:
        sample = SAMPLE_DIR / config.sample_file

    if not sample.exists():
        raise HTTPException(status_code=404, detail=f"Sample file missing for {config.id}.")
    return _run_document(sample, sample.name, config.id)


@router.get("/runs")
def runs(limit: int = 20):
    return list_runs(limit=max(1, min(limit, 100)))


@router.get("/runs/{run_id}", response_model=Run)
def run_detail(run_id: str) -> Run:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run


@router.patch("/runs/{run_id}/records/{index}", response_model=Run)
def edit_record(run_id: str, index: int, edit: RecordEdit) -> Run:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if index < 0 or index >= len(run.records):
        raise HTTPException(status_code=404, detail="Record not found.")

    config = _config(run.vertical)
    field = config.field(edit.field)
    if field is None:
        raise HTTPException(status_code=400, detail=f"Unknown field {edit.field!r}.")

    normalized = normalize_value(edit.value, field)
    raw = "" if edit.value is None else str(edit.value).strip()
    if (
        raw
        and normalized is None
        and (field.type in ("decimal", "int", "float") or field.normalizer == "currency")
    ):
        raise HTTPException(status_code=422, detail=f"{field.label} has an invalid value.")
    if (
        field.normalizer == "date"
        and raw
        and normalized is not None
        and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(normalized))
    ):
        raise HTTPException(status_code=422, detail=f"{field.label} must be a date.")

    run.records[index][field.name] = normalized
    run.warnings = refresh_warnings(run.records, run.warnings, config)
    run.status = run_status(run.records, run.warnings)
    save_run(run)
    return run


@router.get("/runs/{run_id}/export.csv")
def run_export(run_id: str) -> Response:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    config = _config(run.vertical)
    csv_text = export_csv(run.records, config)
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(run.filename).stem).strip("-") or "export"
    filename = f"{stem}-{config.id}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
