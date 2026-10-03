import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Dataset, type QueryResult, type QueryRun, type SavedQuery } from "./api";
import { ResultsTable } from "./components/ResultsTable";
import { Sidebar } from "./components/Sidebar";
import { toCsv } from "./format";

const PAGE_SIZE = 100;
const STARTER = "SELECT start_station, count(*) AS trips, round(avg(duration_min), 1) AS avg_min\nFROM bike_trips\nGROUP BY start_station\nORDER BY trips DESC";

export default function App() {
  const [sql, setSql] = useState(STARTER);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [saved, setSaved] = useState<SavedQuery[]>([]);
  const [history, setHistory] = useState<QueryRun[]>([]);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [ranSql, setRanSql] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const refresh = useCallback(async () => {
    const [d, s, h] = await Promise.all([api.datasets(), api.savedQueries(), api.history()]);
    setDatasets(d);
    setSaved(s);
    setHistory(h);
  }, []);

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [refresh]);

  const run = useCallback(
    async (text: string, toPage = 0) => {
      setRunning(true);
      setError(null);
      try {
        setResult(await api.query(text, PAGE_SIZE, toPage * PAGE_SIZE));
        setRanSql(text);
        setPage(toPage);
      } catch (e) {
        setResult(null);
        setError(e instanceof ApiError && e.status === 408 ? `Timed out: ${e.message}` : e instanceof Error ? e.message : String(e));
      } finally {
        setRunning(false);
        api.history().then(setHistory).catch(() => undefined);
      }
    },
    [],
  );

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      run(sql);
    }
  }

  async function save() {
    const name = window.prompt("Name this query");
    if (!name) return;
    try {
      await api.saveQuery(name, sql);
      setSaved(await api.savedQueries());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function exportCsv() {
    if (!result) return;
    const blob = new Blob([toCsv(result.columns.map((c) => c.name), result.rows)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: "querypad-results.csv" });
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="app">
      <header>
        <h1>QueryPad</h1>
        <span className="muted">SQL workspace for your CSV files</span>
      </header>
      <div className="layout">
        <Sidebar
          datasets={datasets}
          saved={saved}
          history={history}
          onPick={setSql}
          onUpload={async (name, file) => {
            try {
              await api.uploadDataset(name, file);
              setDatasets(await api.datasets());
            } catch (e) {
              setError(e instanceof Error ? e.message : String(e));
            }
          }}
          onDropDataset={async (name) => {
            await api.deleteDataset(name);
            setDatasets(await api.datasets());
          }}
          onDeleteSaved={async (id) => {
            await api.deleteSavedQuery(id);
            setSaved(await api.savedQueries());
          }}
        />
        <main>
          <textarea
            className="editor"
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            onKeyDown={onKeyDown}
            spellCheck={false}
            aria-label="SQL editor"
          />
          <div className="toolbar">
            <button className="primary" onClick={() => run(sql)} disabled={running || !sql.trim()}>
              {running ? "Running…" : "Run"}
            </button>
            <span className="muted small">Ctrl or Cmd + Enter</span>
            <button onClick={save} disabled={!sql.trim()}>
              Save query
            </button>
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          {result && <ResultsTable result={result} page={page} pageSize={PAGE_SIZE} onPage={(p) => run(ranSql, p)} onExport={exportCsv} />}
        </main>
      </div>
    </div>
  );
}
