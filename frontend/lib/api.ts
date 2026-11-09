import type { Run, RunSummary, Vertical } from "./types";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

async function errorMessage(response: Response): Promise<string> {
  const data = (await response.json().catch(() => null)) as { detail?: string } | null;
  return data?.detail ?? `Request failed (${response.status})`;
}

export async function getVerticals(): Promise<Vertical[]> {
  const response = await fetch(`${API_URL}/api/docpipe/verticals`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Vertical[]>;
}

export async function getRuns(): Promise<RunSummary[]> {
  const response = await fetch(`${API_URL}/api/docpipe/runs`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<RunSummary[]>;
}

export async function getRun(id: string): Promise<Run> {
  const response = await fetch(`${API_URL}/api/docpipe/runs/${id}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}

export async function extractFile(file: File, vertical: string): Promise<Run> {
  const form = new FormData();
  form.append("file", file);
  form.append("vertical", vertical);
  const response = await fetch(`${API_URL}/api/docpipe/extract`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}

export async function extractSample(vertical: string): Promise<Run> {
  const response = await fetch(
    `${API_URL}/api/docpipe/extract/sample?vertical=${encodeURIComponent(vertical)}`,
    { method: "POST" }
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}

export function exportUrl(runId: string): string {
  return `${API_URL}/api/docpipe/runs/${runId}/export.csv`;
}
