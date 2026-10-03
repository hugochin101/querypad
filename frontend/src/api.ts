export interface Column {
  name: string;
  type: string;
}

export interface Dataset {
  name: string;
  row_count: number;
  columns: Column[];
}

export interface QueryResult {
  columns: Column[];
  rows: unknown[][];
  has_more: boolean;
  elapsed_ms: number;
  cached: boolean;
}

export interface SavedQuery {
  id: number;
  name: string;
  sql: string;
  created_at: string;
}

export interface QueryRun {
  id: number;
  sql: string;
  status: "ok" | "error" | "timeout" | "rejected";
  elapsed_ms: number | null;
  row_count: number | null;
  error: string | null;
  ran_at: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  datasets: () => request<Dataset[]>("/datasets"),
  uploadDataset: (name: string, file: File) => {
    const form = new FormData();
    form.append("name", name);
    form.append("file", file);
    return request<Dataset>("/datasets", { method: "POST", body: form });
  },
  deleteDataset: (name: string) => request<void>(`/datasets/${encodeURIComponent(name)}`, { method: "DELETE" }),
  query: (sql: string, limit: number, offset: number) =>
    request<QueryResult>("/query", json({ sql, limit, offset })),
  history: () => request<QueryRun[]>("/history"),
  savedQueries: () => request<SavedQuery[]>("/saved-queries"),
  saveQuery: (name: string, sql: string) => request<SavedQuery>("/saved-queries", json({ name, sql })),
  deleteSavedQuery: (id: number) => request<void>(`/saved-queries/${id}`, { method: "DELETE" }),
};
