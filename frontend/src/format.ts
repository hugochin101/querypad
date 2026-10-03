/** Display text for one result cell. */
export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString("en-GB") : value.toLocaleString("en-GB", { maximumFractionDigits: 4 });
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** Quote a CSV field when it contains a delimiter, quote or newline (RFC 4180). */
export function csvField(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function toCsv(columns: string[], rows: unknown[][]): string {
  const lines = [columns.map(csvField).join(","), ...rows.map((r) => r.map(csvField).join(","))];
  return lines.join("\r\n") + "\r\n";
}

/** Suggest a dataset name from a file name: lowercase, underscores, no extension. */
export function datasetNameFromFile(fileName: string): string {
  const base = fileName.replace(/\.[^.]+$/, "").toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "");
  const safe = base || "dataset";
  return /^[a-z_]/.test(safe) ? safe.slice(0, 63) : `_${safe}`.slice(0, 63);
}

export function formatMs(ms: number): string {
  return ms < 1000 ? `${ms.toFixed(1)} ms` : `${(ms / 1000).toFixed(2)} s`;
}
