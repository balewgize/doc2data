import type { Health, Run, RunSummary, Vertical } from "./types";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

async function errorMessage(response: Response): Promise<string> {
  const data = (await response.json().catch(() => null)) as { detail?: string } | null;
  return data?.detail ?? `Request failed (${response.status})`;
}

export async function getVerticals(): Promise<Vertical[]> {
  const response = await fetch(`${API_URL}/api/doc2data/verticals`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Vertical[]>;
}

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_URL}/api/doc2data/health`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Health>;
}

export async function getRuns(limit = 6): Promise<RunSummary[]> {
  const response = await fetch(
    `${API_URL}/api/doc2data/runs?limit=${limit}`,
    { cache: "no-store" }
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<RunSummary[]>;
}

export async function getRun(id: string): Promise<Run> {
  const response = await fetch(`${API_URL}/api/doc2data/runs/${id}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}

export async function extractFile(file: File, vertical: string): Promise<Run> {
  const form = new FormData();
  form.append("file", file);
  form.append("vertical", vertical);
  const response = await fetch(`${API_URL}/api/doc2data/extract`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}

export async function extractSample(
  vertical: string,
  real = false
): Promise<Run> {
  const query = new URLSearchParams({ vertical });
  if (real) query.set("real", "true");
  const response = await fetch(
    `${API_URL}/api/doc2data/extract/sample?${query.toString()}`,
    { method: "POST" }
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}

export type ExtractionProgress = {
  stage: string;
  message: string;
  current?: number;
  total?: number;
};

async function readStream(
  response: Response,
  onProgress?: (progress: ExtractionProgress) => void
): Promise<Run> {
  if (!response.ok) throw new Error(await errorMessage(response));
  if (!response.body) throw new Error("This browser cannot stream progress updates.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let run: Run | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");

      const data = frame
        .split("\n")
        .find((line) => line.startsWith("data:"))
        ?.slice(5)
        .trim();
      if (!data) continue;

      const event = JSON.parse(data) as ExtractionProgress & { run?: Run };
      onProgress?.(event);
      if (event.stage === "error") throw new Error(event.message);
      if (event.stage === "done" && event.run) run = event.run;
    }
  }

  if (!run) throw new Error("The extraction stream ended without a result.");
  return run;
}

export async function extractFileStream(
  file: File,
  vertical: string,
  onProgress?: (progress: ExtractionProgress) => void
): Promise<Run> {
  const form = new FormData();
  form.append("file", file);
  form.append("vertical", vertical);
  const response = await fetch(`${API_URL}/api/doc2data/extract/stream`, {
    method: "POST",
    body: form,
  });
  return readStream(response, onProgress);
}

export async function extractSampleStream(
  vertical: string,
  real = false,
  onProgress?: (progress: ExtractionProgress) => void
): Promise<Run> {
  const query = new URLSearchParams({ vertical });
  if (real) query.set("real", "true");
  const response = await fetch(
    `${API_URL}/api/doc2data/extract/sample/stream?${query.toString()}`,
    { method: "POST" }
  );
  return readStream(response, onProgress);
}

export function exportUrl(runId: string): string {
  return `${API_URL}/api/doc2data/runs/${runId}/export.csv`;
}

export function sourceUrl(runId: string): string {
  return `${API_URL}/api/doc2data/runs/${runId}/source`;
}

export async function updateRecord(
  runId: string,
  index: number,
  field: string,
  value: unknown
): Promise<Run> {
  const response = await fetch(
    `${API_URL}/api/doc2data/runs/${runId}/records/${index}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, value }),
    }
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Run>;
}
