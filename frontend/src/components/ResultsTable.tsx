import type { QueryResult } from "../api";
import { formatCell, formatMs } from "../format";

interface Props {
  result: QueryResult;
  page: number;
  pageSize: number;
  onPage: (page: number) => void;
  onExport: () => void;
}

export function ResultsTable({ result, page, pageSize, onPage, onExport }: Props) {
  const first = page * pageSize + 1;
  const last = page * pageSize + result.rows.length;

  return (
    <section className="results" aria-label="Query results">
      <div className="results-bar">
        <span>
          {result.rows.length === 0 ? "No rows" : `Rows ${first.toLocaleString("en-GB")} to ${last.toLocaleString("en-GB")}`}
          {" · "}
          {result.cached ? "served from cache" : formatMs(result.elapsed_ms)}
        </span>
        <span className="results-actions">
          <button onClick={() => onPage(page - 1)} disabled={page === 0}>
            Previous
          </button>
          <button onClick={() => onPage(page + 1)} disabled={!result.has_more}>
            Next
          </button>
          <button onClick={onExport} disabled={result.rows.length === 0}>
            Export page as CSV
          </button>
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {result.columns.map((c) => (
                <th key={c.name} title={c.type}>
                  {c.name}
                  <span className="col-type">{c.type}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j} className={cell === null ? "null" : typeof cell === "number" ? "num" : undefined}>
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
