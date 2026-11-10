"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  API_URL,
  exportUrl,
  extractFile,
  extractSample,
  getHealth,
  getRun,
  getRuns,
  getVerticals,
  updateRecord,
} from "@/lib/api";
import type { Health, Run, RunSummary, Vertical } from "@/lib/types";

const STATUS_LABEL: Record<Run["status"], string> = {
  ok: "Ready",
  review: "Needs review",
  error: "Failed",
};

function StatusBadge({ status }: { status: string }) {
  const key = status in STATUS_LABEL ? (status as Run["status"]) : "review";
  return (
    <span className={`status status--${key}`}>
      {STATUS_LABEL[key]}
    </span>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function toDraft(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatBytes(value: unknown): string {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return "—";
  if (number < 1024) return `${number} B`;
  if (number < 1024 * 1024) return `${(number / 1024).toFixed(1)} KB`;
  return `${(number / (1024 * 1024)).toFixed(1)} MB`;
}

type EditableCellProps = {
  runId: string;
  recordIndex: number;
  field: string;
  label: string;
  value: unknown;
  onSaved: (run: Run) => void;
  onError: (message: string) => void;
};

function EditableCell({
  runId,
  recordIndex,
  field,
  label,
  value,
  onSaved,
  onError,
}: EditableCellProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const cancelled = useRef(false);

  function startEditing() {
    cancelled.current = false;
    setDraft(toDraft(value));
    setEditing(true);
  }

  function cancelEditing() {
    cancelled.current = true;
    setEditing(false);
  }

  async function save() {
    if (savingRef.current || cancelled.current) {
      cancelled.current = false;
      return;
    }
    savingRef.current = true;
    setSaving(true);
    try {
      const updated = await updateRecord(runId, recordIndex, field, draft);
      setEditing(false);
      onSaved(updated);
    } catch (reason) {
      onError(
        reason instanceof Error ? reason.message : "Could not save the change."
      );
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <button
        type="button"
        className="cellbtn"
        title={`Edit ${label}`}
        aria-label={`Edit ${label}: ${formatValue(value)}`}
        onClick={startEditing}
      >
        {formatValue(value)}
      </button>
    );
  }

  return (
    <input
      className="cellinput"
      value={draft}
      autoFocus
      disabled={saving}
      aria-label={`Edit ${label}`}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => void save()}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          void save();
        } else if (event.key === "Escape") {
          event.preventDefault();
          cancelEditing();
        }
      }}
    />
  );
}

type Pending = "file" | "sample" | "real" | "load" | null;

export default function Home() {
  const [verticals, setVerticals] = useState<Vertical[]>([]);
  const [vertical, setVertical] = useState("ecommerce");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [booted, setBooted] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [error, setError] = useState<string | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [stageError, setStageError] = useState<string | null>(null);
  const [runsError, setRunsError] = useState<string | null>(null);

  const loading = pending !== null;
  const databaseName = health?.database?.split("/").pop() ?? null;
  const liveProvider = health?.provider === "ollama" || health?.provider === "openai";
  const providerLabel =
    health?.provider === "ollama"
      ? "Ollama"
      : health?.provider === "openai"
        ? "OpenAI"
        : null;

  const selected = useMemo(
    () => verticals.find((item) => item.id === vertical),
    [verticals, vertical]
  );

  const refreshRuns = useCallback(async () => {
    setRunsError(null);
    try {
      setRuns(await getRuns());
    } catch {
      setRunsError("Recent runs did not refresh. Try again.");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getVerticals(), getRuns(), getHealth()])
      .then(async ([verticalList, runList, healthState]) => {
        if (cancelled) return;
        setVerticals(verticalList);
        setRuns(runList);
        setHealth(healthState);
        if (verticalList.length) {
          setVertical((current) =>
            verticalList.some((v) => v.id === current) ? current : verticalList[0].id
          );
        }
        // Show the product's own last result on arrival; the review stage is the point.
        if (runList.length) {
          try {
            const latest = await getRun(runList[0].id);
            if (!cancelled) setRun(latest);
          } catch {
            // The setup rail still works without a loaded run.
          }
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Could not reach the API.");
          setRunsError("Recent runs did not load.");
          setStageError("The review stage did not load. Check the API and refresh.");
        }
      })
      .finally(() => {
        if (!cancelled) setBooted(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleExtract(useSample = false, real = false) {
    if (!useSample && !file) {
      setExtractError("Choose a document first, or try the sample.");
      return;
    }
    setPending(real ? "real" : useSample ? "sample" : "file");
    setExtractError(null);
    setStageError(null);
    try {
      const result = useSample
        ? await extractSample(vertical, real)
        : await extractFile(file as File, vertical);
      setRun(result);
      await refreshRuns();
    } catch (reason) {
      setExtractError(
        reason instanceof Error ? reason.message : "Extraction failed."
      );
    } finally {
      setPending(null);
    }
  }

  async function handleLoadRun(id: string) {
    setPending("load");
    setStageError(null);
    try {
      setRun(await getRun(id));
    } catch (reason) {
      setStageError(
        reason instanceof Error ? reason.message : "Could not load that run."
      );
    } finally {
      setPending(null);
    }
  }

  function handleRecordSaved(updated: Run) {
    setRun((current) => (current?.id === updated.id ? updated : current));
    setStageError(null);
    void refreshRuns();
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }

  const visibleColumns = useMemo(() => {
    if (!run) return [];
    const hidden = new Set(["description", "seo_title", "seo_description", "image_urls"]);
    return run.columns.filter((column) => !hidden.has(column.key));
  }, [run]);

  const sortedWarnings = useMemo(() => {
    if (!run) return [];
    const order = { error: 0, warning: 1, info: 2 };
    return [...run.warnings].sort((a, b) => order[a.severity] - order[b.severity]);
  }, [run]);

  const realSampleLabel =
    selected?.id === "ecommerce"
      ? "Try public catalog"
      : selected?.id === "finance"
        ? "Try public invoice"
        : selected?.id === "logistics"
          ? "Try public BOL"
          : selected?.id === "healthcare"
            ? "Try public claim"
            : "Try public sample";

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to main content
      </a>

      <header className="topbar">
        <div className="container topbar__in">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              D2D
            </span>
            <span className="brand__text">
              <span className="brand__name">Doc2Data</span>
              <span className="brand__line">Documents in. Clean data out.</span>
            </span>
          </div>
          <div className="topbar__links">
            <a
              className="btn"
              href="https://github.com/balewgize/doc2data"
              target="_blank"
              rel="noreferrer"
            >
              Source
            </a>
            <a
              className="btn"
              href={`${API_URL}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              API docs
            </a>
          </div>
        </div>
      </header>

      <main id="main">
        <section className="intro" aria-labelledby="page-title">
          <div className="container intro__grid">
            <div className="intro__text">
              <h1 id="page-title">Turn messy documents into validated records.</h1>
              <p>
                Operations teams still retype supplier catalogs, invoices, shipment
                notes and claims by hand. Doc2Data extracts the fields with an LLM,
                normalizes units and currencies, flags missing or conflicting values,
                and lets you correct them inline before exporting an import-ready CSV.
                One engine, four industry schemas.
              </p>
            </div>
            <dl className="specs" aria-label="Extraction environment">
              <div>
                <dt>Provider</dt>
                <dd>{health?.provider ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{health?.model ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Database</dt>
                <dd>{databaseName ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Upload limit</dt>
                <dd>{health?.max_upload_mb ?? 20} MB</dd>
              </div>
            </dl>
          </div>
        </section>

        {error && (
          <div className="container alertwrap">
            <div role="alert" className="alert">
              {error}
            </div>
          </div>
        )}

        <div className="container workbench">
          <div className="rail">
            <section className="block" aria-labelledby="industries-title">
              <h2 id="industries-title">
                <span className="step">1.</span> Pick an industry
              </h2>
              <p className="block__line">
                The same pipeline, different schemas and export rules.
              </p>

              <div className="choices" role="group" aria-label="Industry">
                {verticals.map((item) => {
                  const active = item.id === vertical;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setVertical(item.id)}
                      aria-pressed={active}
                      className="choice"
                    >
                      <span className="choice__label">{item.label}</span>
                      <span className="choice__desc">{item.description}</span>
                    </button>
                  );
                })}
              </div>
              {!verticals.length && (
                <p className="muted-line">
                  {booted ? "No industries loaded." : "Loading industries…"}
                </p>
              )}
            </section>

            <section className="block" aria-labelledby="document-title">
              <h2 id="document-title">
                <span className="step">2.</span> Add a document
              </h2>

              <label
                className={dragging ? "drop is-dragging" : "drop"}
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  name="file"
                  className="visually-hidden"
                  accept=".pdf,.xlsx,.xlsm,.csv,.txt,.md,.json"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  className="drop__icon"
                  width="26"
                  height="26"
                >
                  <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" strokeLinecap="round" />
                </svg>
                <span className="drop__name">
                  {file ? file.name : "Drop a file here, or click to browse"}
                </span>
                <span className="drop__meta">
                  {file
                    ? `${formatBytes(file.size)}, ${file.type || "unknown type"}`
                    : "PDF, XLSX, CSV, TXT, MD or JSON, up to 20 MB"}
                </span>
              </label>

              <div className="fileline">
                {file && (
                  <button
                    type="button"
                    className="linkbtn"
                    onClick={() => setFile(null)}
                  >
                    Clear file
                  </button>
                )}
              </div>

              <div className="actions">
                <button
                  type="button"
                  onClick={() => handleExtract(false)}
                  disabled={loading || !file}
                  className="btn btn--primary"
                  aria-describedby="extract-help"
                >
                  Extract records
                </button>
                <button
                  type="button"
                  onClick={() => handleExtract(true)}
                  disabled={loading}
                  className="btn"
                >
                  Try the sample
                </button>
                {selected?.real_sample && (
                  <button
                    type="button"
                    onClick={() => handleExtract(true, true)}
                    disabled={loading}
                    title={
                      liveProvider
                        ? `Run the public sample live with ${providerLabel}`
                        : "Load a bundled result from a public sample, or configure Ollama or OpenAI to re-extract it live"
                    }
                    className="btn btn--wide"
                  >
                    {realSampleLabel}
                  </button>
                )}
              </div>

              {extractError && (
                <p className="inline-alert" role="alert">
                  {extractError}
                </p>
              )}

              {(pending === "file" || pending === "sample" || pending === "real") && (
                <p className="statusline" role="status">
                  <span className="spinner" aria-hidden="true" />
                  {pending === "file"
                    ? "Extracting records…"
                    : pending === "real"
                      ? "Running the public sample…"
                      : "Running the sample…"}
                </p>
              )}

              <p className="helpline helpline--reserved" id="extract-help">
                Extract needs a file. Either sample runs without one.
              </p>
              <p className="helpline">
                {liveProvider
                  ? `Public samples run live with ${providerLabel}. Local extraction can take a minute.`
                  : "Public samples are bundled with the project. They run offline in demo mode; set Ollama (gemma3:1b) or OpenAI to re-extract them live."}
              </p>
            </section>

          </div>

          <section className="stage" aria-labelledby="review-title">
            <div className="stage__card" aria-busy={pending === "load"}>
              <div className="stage__head">
                <div>
                  <h2 id="review-title">
                    <span className="step">3.</span> Review and export
                  </h2>
                  <p className="stage__sub">
                    Click any value to correct it. Review notes and the CSV update
                    immediately.
                  </p>
                </div>
                {run && (
                  <a
                    href={exportUrl(run.id)}
                    className="btn btn--primary"
                  >
                    Download CSV
                  </a>
                )}
              </div>

              {stageError && (
                <p className="inline-alert" role="alert">
                  {stageError}
                </p>
              )}

              {pending === "load" && (
                <p className="statusline" role="status">
                  <span className="spinner" aria-hidden="true" />
                  Opening run…
                </p>
              )}

              {!run ? (
                <div className="empty">
                  <p className="empty__title">
                    {booted ? "No run yet" : "Loading the latest run…"}
                  </p>
                  <p className="empty__line">
                    Upload a document or load the sample to see the review screen.
                  </p>
                  {booted && (
                    <button
                      type="button"
                      onClick={() => handleExtract(true)}
                      disabled={loading}
                      className="btn"
                    >
                      Try the sample
                    </button>
                  )}
                </div>
              ) : (
                <div>
                  <div className="runhead">
                    <StatusBadge status={run.status} />
                    <span className="runhead__file">{run.filename}</span>
                    <span className="runhead__meta">{run.vertical_label}</span>
                    <span className="runhead__meta">{run.provider}</span>
                    <span className="runhead__meta">{formatDate(run.created_at)}</span>
                  </div>

                  {run.meta.public_sample === true && (
                    <p className="helpline">
                      Bundled demo result for a public sample. Configure OpenAI or
                      Ollama to run the document live.
                    </p>
                  )}

                  <dl className="figures">
                    {[
                      ["Records", String(run.records.length)],
                      ["Review notes", String(run.warnings.length)],
                      ["Chunks", String(run.meta.chunks ?? "—")],
                      [
                        "Source text",
                        `${Number(run.meta.source_chars ?? 0).toLocaleString()} chars`,
                      ],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <dt className="figure__label">{label}</dt>
                        <dd className="figure__value">{value}</dd>
                      </div>
                    ))}
                  </dl>

                  {run.records.length > 0 && (
                    <p className="tablehint">
                      Click any value to edit.
                      {visibleColumns.length > 6
                        ? ` ${visibleColumns.length} columns, scroll to see them all.`
                        : ""}
                    </p>
                  )}

                  <div className="tablescroll">
                    <div
                      className="tablewrap"
                      role="region"
                      aria-label="Extracted records. Click a value to edit, or scroll horizontally."
                      tabIndex={0}
                    >
                      <table>
                        <caption className="visually-hidden">
                          Extracted records. Click a value to edit.
                        </caption>
                        <thead>
                          <tr>
                            {visibleColumns.map((column) => (
                              <th
                                key={column.key}
                                scope="col"
                                className={
                                  ["int", "float", "decimal"].includes(column.type)
                                    ? "num"
                                    : undefined
                                }
                              >
                                {column.label}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {run.records.map((record, index) => (
                            <tr key={index}>
                              {visibleColumns.map((column) => (
                                <td
                                  key={column.key}
                                  className={
                                    ["int", "float", "decimal"].includes(column.type)
                                      ? "num"
                                      : undefined
                                  }
                                >
                                  <EditableCell
                                    runId={run.id}
                                    recordIndex={index}
                                    field={column.key}
                                    label={column.label}
                                    value={record[column.key]}
                                    onSaved={handleRecordSaved}
                                    onError={(message) => setStageError(message)}
                                  />
                                </td>
                              ))}
                            </tr>
                          ))}
                          {!run.records.length && (
                            <tr>
                              <td
                                colSpan={Math.max(visibleColumns.length, 1)}
                                className="tableempty"
                              >
                                No records extracted.
                              </td>
                            </tr>
                          )}
                        </tbody>
                        </table>
                    </div>
                  </div>

                  {sortedWarnings.length > 0 && (
                    <div className="notes">
                      <h3>
                        Review notes
                        <span className="notes__count">
                          ({sortedWarnings.length})
                        </span>
                      </h3>
                      <ul className="notelist">
                        {sortedWarnings.map((warning, index) => (
                          <li key={`${warning.code}-${index}`} className="note">
                            <span className={`note__sev note__sev--${warning.severity}`}>
                              {warning.severity === "error"
                                ? "Error"
                                : warning.severity === "warning"
                                  ? "Warning"
                                  : "Info"}
                            </span>
                            <div>
                              <p className="note__msg">{warning.message}</p>
                              {(warning.record_key || warning.code) && (
                                <p className="note__meta">
                                  {warning.record_key && (
                                    <span>{warning.record_key}</span>
                                  )}
                                  {warning.code && <span>{warning.code}</span>}
                                </p>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
          <section className="block recent" aria-labelledby="recent-title">
            <div className="block__head">
              <h2 id="recent-title">Recent runs</h2>
              <button
                type="button"
                onClick={refreshRuns}
                className="linkbtn"
              >
                Refresh
              </button>
            </div>
            {runsError && (
              <p className="inline-alert" role="alert">
                {runsError}
              </p>
            )}
            <ul className="runs">
              {runs.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => handleLoadRun(item.id)}
                    className="run"
                    aria-current={run?.id === item.id ? "true" : undefined}
                  >
                    <span className="run__file">{item.filename}</span>
                    <span className={`run__state run__state--${item.status}`}>
                      {STATUS_LABEL[item.status] ?? STATUS_LABEL.review}
                    </span>
                    <span className="run__meta">
                      {item.vertical_label}, {item.record_count} records,{" "}
                      {formatDate(item.created_at)}
                    </span>
                  </button>
                </li>
              ))}
              {!runs.length && !runsError && (
                <li className="runs__empty">
                  {booted
                    ? "No runs yet. Try the sample, or add a document."
                    : "Loading recent runs…"}
                </li>
              )}
            </ul>
          </section>
        </div>

        <section className="band" aria-labelledby="about-title">
          <div className="container band__grid">
            <div className="band__col">
              <h2 id="about-title">The problem</h2>
              <p>
                Every operations team has someone retyping data from PDFs, spreadsheets
                and emails into Shopify, an ERP, a ledger or a warehouse system. It is
                slow, error-prone and expensive.
              </p>
              <p>
                Chat-with-your-PDF tools return text. The hard part is a clean,
                validated record in the system of record, and that is the workflow
                Doc2Data is built around.
              </p>
            </div>
            <div className="band__col band__col--status">
              <h2>What it handles</h2>
              <p>
                PDF, XLSX, CSV, TXT, MD and JSON in, an import-ready CSV out. Extract
                with OpenAI, Ollama or the deterministic offline provider, then
                normalize units, currencies, prices and dimensions.
              </p>
              <p>
                Validation covers required fields, duplicates, totals and cross-field
                rules. Review notes point at the record that needs attention, every
                value edits inline, and an edit is re-validated before export.
              </p>
              <ul className="tags">
                {[
                  "schema validation",
                  "inline correction",
                  "CSV export",
                  "provider-agnostic",
                  "public samples",
                  "run history",
                ].map((tag) => (
                  <li key={tag}>{tag}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container footer__in">
          <p>Doc2Data by Alemnew Marie. Documents in. Clean data out.</p>
          <p>
            Single-user build on FastAPI, Next.js and SQLite.{" "}
            <a
              href="https://github.com/balewgize/doc2data"
              target="_blank"
              rel="noreferrer"
            >
              Source on GitHub
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
