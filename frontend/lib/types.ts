export type Field = {
  name: string;
  label: string;
  type: string;
  required: boolean;
  recommended: boolean;
};

export type Vertical = {
  id: string;
  label: string;
  description: string;
  ready: boolean;
  fields: Field[];
};

export type Warning = {
  code: string;
  message: string;
  severity: "error" | "warning" | "info";
  record_key?: string | null;
};

export type Column = {
  key: string;
  label: string;
  type: string;
};

export type Run = {
  id: string;
  created_at: string;
  vertical: string;
  vertical_label: string;
  filename: string;
  provider: string;
  status: "ok" | "review" | "error";
  records: Record<string, unknown>[];
  warnings: Warning[];
  columns: Column[];
  meta: Record<string, unknown>;
};

export type RunSummary = {
  id: string;
  created_at: string;
  vertical: string;
  vertical_label: string;
  filename: string;
  provider: string;
  status: "ok" | "review" | "error";
  record_count: number;
  warning_count: number;
};
