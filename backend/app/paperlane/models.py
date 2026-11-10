"""API-facing models for Paperlane runs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["error", "warning", "info"]


class Column(BaseModel):
    key: str
    label: str
    type: str


class WarningItem(BaseModel):
    code: str
    message: str
    severity: Severity = "warning"
    record_key: str | None = None


class RunSummary(BaseModel):
    id: str
    created_at: str
    vertical: str
    vertical_label: str
    filename: str
    provider: str
    status: Literal["ok", "review", "error"]
    record_count: int
    warning_count: int


class Run(BaseModel):
    id: str
    created_at: str
    vertical: str
    vertical_label: str
    filename: str
    provider: str
    status: Literal["ok", "review", "error"]
    records: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    columns: list[Column] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
