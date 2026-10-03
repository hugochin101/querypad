import { useRef, useState } from "react";
import type { Dataset, QueryRun, SavedQuery } from "../api";
import { datasetNameFromFile, formatMs } from "../format";

interface Props {
  datasets: Dataset[];
  saved: SavedQuery[];
  history: QueryRun[];
  onUpload: (name: string, file: File) => Promise<void>;
  onDropDataset: (name: string) => void;
  onPick: (sql: string) => void;
  onDeleteSaved: (id: number) => void;
}

type Tab = "data" | "saved" | "history";

export function Sidebar({ datasets, saved, history, onUpload, onDropDataset, onPick, onDeleteSaved }: Props) {
  const [tab, setTab] = useState<Tab>("data");
  const [open, setOpen] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    try {
      await onUpload(datasetNameFromFile(file.name), file);
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  return (
    <aside className="sidebar">
      <div className="tabs" role="tablist">
        {(["data", "saved", "history"] as Tab[]).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "data" ? "Datasets" : t === "saved" ? "Saved" : "History"}
          </button>
        ))}
      </div>

      {tab === "data" && (
        <div className="panel">
          <label className="upload">
            {uploading ? "Uploading…" : "Upload CSV"}
            <input ref={fileInput} type="file" accept=".csv" disabled={uploading} onChange={(e) => handleFile(e.target.files?.[0])} />
          </label>
          {datasets.length === 0 && <p className="muted">No datasets yet. Upload a CSV to start.</p>}
          <ul className="list">
            {datasets.map((d) => (
              <li key={d.name}>
                <div className="row">
                  <button className="link" onClick={() => setOpen(open === d.name ? null : d.name)} aria-expanded={open === d.name}>
                    {d.name}
                  </button>
                  <span className="muted">{d.row_count.toLocaleString("en-GB")} rows</span>
                </div>
                {open === d.name && (
                  <div className="schema">
                    <ul>
                      {d.columns.map((c) => (
                        <li key={c.name}>
                          <code>{c.name}</code> <span className="muted">{c.type}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="row">
                      <button className="link" onClick={() => onPick(`SELECT *\nFROM ${d.name}\nLIMIT 100`)}>
                        Preview
                      </button>
                      <button className="link danger" onClick={() => onDropDataset(d.name)}>
                        Remove
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "saved" && (
        <div className="panel">
          {saved.length === 0 && <p className="muted">Save a query to keep it here.</p>}
          <ul className="list">
            {saved.map((q) => (
              <li key={q.id} className="row">
                <button className="link" onClick={() => onPick(q.sql)} title={q.sql}>
                  {q.name}
                </button>
                <button className="link danger" aria-label={`Delete ${q.name}`} onClick={() => onDeleteSaved(q.id)}>
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "history" && (
        <div className="panel">
          {history.length === 0 && <p className="muted">Queries you run appear here.</p>}
          <ul className="list">
            {history.map((h) => (
              <li key={h.id}>
                <button className="link sql" onClick={() => onPick(h.sql)} title={h.error ?? h.sql}>
                  {h.sql}
                </button>
                <div className="muted small">
                  <span className={`status ${h.status}`}>{h.status}</span>
                  {h.elapsed_ms != null && ` · ${formatMs(h.elapsed_ms)}`}
                  {h.row_count != null && ` · ${h.row_count} rows`}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
