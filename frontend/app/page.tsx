"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  API_URL,
  exportUrl,
  extractFile,
  extractSample,
  getRun,
  getRuns,
  getVerticals,
} from "@/lib/api";
import type { Run, RunSummary, Vertical } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  ok: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20",
  review:
    "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20",
  error:
    "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${
        STATUS_STYLES[status] ?? STATUS_STYLES.review
      }`}
    >
      {status}
    </span>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
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

export default function Home() {
  const [verticals, setVerticals] = useState<Vertical[]>([]);
  const [vertical, setVertical] = useState("ecommerce");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(
    () => verticals.find((item) => item.id === vertical),
    [verticals, vertical]
  );

  const refreshRuns = useCallback(async () => {
    try {
      setRuns(await getRuns());
    } catch {
      // Recent runs are secondary; the main error banner covers API failures.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getVerticals(), getRuns()])
      .then(([verticalList, runList]) => {
        if (cancelled) return;
        setVerticals(verticalList);
        setRuns(runList);
        if (verticalList.length) {
          setVertical((current) =>
            verticalList.some((v) => v.id === current) ? current : verticalList[0].id
          );
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Could not reach the API.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleExtract(useSample = false) {
    if (!useSample && !file) {
      setError("Choose a document first, or try the sample.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = useSample
        ? await extractSample(vertical)
        : await extractFile(file as File, vertical);
      setRun(result);
      await refreshRuns();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Extraction failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadRun(id: string) {
    setLoading(true);
    setError(null);
    try {
      setRun(await getRun(id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load that run.");
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="min-h-screen bg-[#f7f7f5] text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <header className="border-b border-zinc-200/80 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 text-sm font-bold text-white dark:bg-white dark:text-zinc-900">
              PL
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">Paperlane</p>
              <p className="text-xs text-zinc-500">Documents in. Clean data out.</p>
            </div>
          </div>
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 transition hover:border-zinc-400 hover:text-zinc-900 dark:border-zinc-800 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:text-zinc-100"
          >
            API docs
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 max-w-2xl">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Turn messy documents into validated records.
          </h1>
          <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            Upload a supplier catalog, invoice, shipment note or claim. Paperlane
            extracts structured fields, flags missing or conflicting data, and exports
            a clean CSV — one core engine, multiple industries.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
          >
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-semibold">1. Pick an industry</h2>
                  <p className="mt-1 text-sm text-zinc-500">
                    The same pipeline, different schemas and export rules.
                  </p>
                </div>
                {selected && !selected.ready && (
                  <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                    beta
                  </span>
                )}
              </div>

              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {verticals.map((item) => {
                  const active = item.id === vertical;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setVertical(item.id)}
                      className={`rounded-xl border p-3 text-left transition ${
                        active
                          ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900"
                          : "border-zinc-200 bg-white hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">{item.label}</span>
                        <span
                          className={`text-[10px] font-medium uppercase tracking-wide ${
                            active ? "text-white/60 dark:text-zinc-600" : "text-zinc-400"
                          }`}
                        >
                          {item.ready ? "live" : "beta"}
                        </span>
                      </div>
                      <p
                        className={`mt-1 line-clamp-2 text-xs leading-5 ${
                          active ? "text-white/70 dark:text-zinc-600" : "text-zinc-500"
                        }`}
                      >
                        {item.description}
                      </p>
                    </button>
                  );
                })}
                {!verticals.length && (
                  <div className="rounded-xl border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-700">
                    Loading industries…
                  </div>
                )}
              </div>

              <div className="mt-6">
                <h2 className="text-base font-semibold">2. Add a document</h2>
                <label
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  className={`mt-3 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
                    dragging
                      ? "border-emerald-500 bg-emerald-50/60 dark:bg-emerald-500/10"
                      : "border-zinc-300 bg-zinc-50/60 hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-950/40 dark:hover:border-zinc-600"
                  }`}
                >
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.xlsx,.xlsm,.csv,.txt,.md,.json"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  />
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    className="h-7 w-7 text-zinc-400"
                  >
                    <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" strokeLinecap="round" />
                  </svg>
                  <p className="mt-3 text-sm font-medium">
                    {file ? file.name : "Drop a file here, or click to browse"}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {file
                      ? `${formatBytes(file.size)} · ${file.type || "unknown type"}`
                      : "PDF, XLSX, CSV, TXT, MD or JSON · up to 20 MB"}
                  </p>
                </label>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleExtract(false)}
                    disabled={loading || !file}
                    className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                  >
                    {loading ? (
                      <>
                        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
                        Extracting…
                      </>
                    ) : (
                      "Extract records"
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExtract(true)}
                    disabled={loading}
                    className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 transition hover:border-zinc-400 disabled:opacity-40 dark:border-zinc-700 dark:text-zinc-300 dark:hover:border-zinc-500"
                  >
                    Try the sample
                  </button>
                  {file && (
                    <button
                      type="button"
                      onClick={() => setFile(null)}
                      className="text-sm text-zinc-500 underline-offset-4 hover:underline"
                    >
                      Clear file
                    </button>
                  )}
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-semibold">3. Review and export</h2>
                  <p className="mt-1 text-sm text-zinc-500">
                    Validate before anything reaches Shopify, your ledger, or a warehouse system.
                  </p>
                </div>
                {run && (
                  <a
                    href={exportUrl(run.id)}
                    className="rounded-lg bg-emerald-600 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
                  >
                    Download CSV
                  </a>
                )}
              </div>

              {!run ? (
                <div className="mt-6 rounded-xl border border-dashed border-zinc-300 px-6 py-12 text-center dark:border-zinc-700">
                  <p className="text-sm font-medium">No run yet</p>
                  <p className="mt-1 text-sm text-zinc-500">
                    Upload a document or load the sample to see the review screen.
                  </p>
                </div>
              ) : (
                <div className="mt-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusBadge status={run.status} />
                    <span className="text-sm font-medium">{run.filename}</span>
                    <span className="text-xs text-zinc-500">{run.vertical_label}</span>
                    <span className="text-xs text-zinc-400">
                      {run.provider} · {formatDate(run.created_at)}
                    </span>
                  </div>

                  <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      ["Records", String(run.records.length)],
                      ["Review notes", String(run.warnings.length)],
                      ["Chunks", String(run.meta.chunks ?? "—")],
                      [
                        "Source text",
                        `${Number(run.meta.source_chars ?? 0).toLocaleString()} chars`,
                      ],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        className="rounded-xl bg-zinc-50 px-3 py-3 dark:bg-zinc-950/60"
                      >
                        <dt className="text-[11px] uppercase tracking-wide text-zinc-500">
                          {label}
                        </dt>
                        <dd className="mt-1 text-lg font-semibold tabular-nums">{value}</dd>
                      </div>
                    ))}
                  </dl>

                  <div className="mt-6 overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
                    <table className="min-w-full divide-y divide-zinc-200 text-left text-sm dark:divide-zinc-800">
                      <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:bg-zinc-950/60">
                        <tr>
                          {visibleColumns.map((column) => (
                            <th key={column.key} className="whitespace-nowrap px-3 py-2.5 font-medium">
                              {column.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {run.records.map((record, index) => (
                          <tr key={index} className="hover:bg-zinc-50/70 dark:hover:bg-zinc-800/40">
                            {visibleColumns.map((column) => {
                              const value = formatValue(record[column.key]);
                              return (
                                <td
                                  key={column.key}
                                  title={value}
                                  className="max-w-[220px] truncate whitespace-nowrap px-3 py-2.5 text-zinc-700 dark:text-zinc-300"
                                >
                                  {value}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                        {!run.records.length && (
                          <tr>
                            <td
                              colSpan={Math.max(visibleColumns.length, 1)}
                              className="px-3 py-8 text-center text-zinc-500"
                            >
                              No records extracted.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {sortedWarnings.length > 0 && (
                    <div className="mt-6">
                      <h3 className="text-sm font-semibold">
                        Review notes{" "}
                        <span className="font-normal text-zinc-500">
                          ({sortedWarnings.length})
                        </span>
                      </h3>
                      <ul className="mt-3 space-y-2">
                        {sortedWarnings.map((warning, index) => (
                          <li
                            key={`${warning.code}-${index}`}
                            className="flex gap-3 rounded-lg border border-zinc-200 px-3 py-2.5 text-sm dark:border-zinc-800"
                          >
                            <span
                              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                                warning.severity === "error"
                                  ? "bg-red-500"
                                  : warning.severity === "warning"
                                    ? "bg-amber-500"
                                    : "bg-sky-500"
                              }`}
                            />
                            <div className="min-w-0">
                              <p className="text-zinc-700 dark:text-zinc-300">
                                {warning.message}
                              </p>
                              <p className="mt-0.5 text-xs text-zinc-400">
                                {warning.record_key ? `${warning.record_key} · ` : ""}
                                {warning.code}
                              </p>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="text-sm font-semibold">Why this exists</h2>
              <div className="mt-3 space-y-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
                <p>
                  Companies pay people to retype supplier documents into Shopify,
                  ERPs and ledgers. That is the workflow this product replaces.
                </p>
                <p>
                  The core is shared. Each industry adds a schema, a prompt and an
                  export mapping — not a new app.
                </p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {["schema validation", "human review", "CSV export"].map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold">Recent runs</h2>
                <button
                  type="button"
                  onClick={refreshRuns}
                  className="text-xs text-zinc-500 underline-offset-4 hover:underline"
                >
                  Refresh
                </button>
              </div>
              <ul className="mt-3 space-y-2">
                {runs.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => handleLoadRun(item.id)}
                      className="w-full rounded-xl border border-zinc-200 px-3 py-2.5 text-left transition hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium">{item.filename}</span>
                        <span
                          className={`h-2 w-2 shrink-0 rounded-full ${
                            item.status === "ok"
                              ? "bg-emerald-500"
                              : item.status === "error"
                                ? "bg-red-500"
                                : "bg-amber-500"
                          }`}
                        />
                      </div>
                      <p className="mt-0.5 text-xs text-zinc-500">
                        {item.vertical_label} · {item.record_count} records ·{" "}
                        {formatDate(item.created_at)}
                      </p>
                    </button>
                  </li>
                ))}
                {!runs.length && (
                  <li className="rounded-xl border border-dashed border-zinc-300 px-3 py-6 text-center text-sm text-zinc-500 dark:border-zinc-700">
                    No runs yet.
                  </li>
                )}
              </ul>
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-zinc-900 p-5 text-zinc-100 shadow-sm dark:border-zinc-800">
              <h2 className="text-sm font-semibold">MVP status</h2>
              <p className="mt-2 text-xs leading-5 text-zinc-400">
                E-commerce is live. Finance, logistics and healthcare share the same
                engine and are marked beta until their prompts are tuned on real
                documents.
              </p>
              <p className="mt-3 text-xs leading-5 text-zinc-500">
                Offline demo uses the deterministic mock provider. Set{" "}
                <code className="rounded bg-zinc-800 px-1 py-0.5">LLM_PROVIDER=openai</code>{" "}
                or <code className="rounded bg-zinc-800 px-1 py-0.5">ollama</code> for
                real extraction.
              </p>
            </section>
          </aside>
        </div>
      </main>

      <footer className="border-t border-zinc-200/80 py-6 dark:border-zinc-800">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-6 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
          <p>Paperlane · a document-to-data engine for real back-office workflows.</p>
          <p>Built on FastAPI + Next.js · SQLite for the MVP.</p>
        </div>
      </footer>
    </div>
  );
}
