import { fireEvent, render, screen } from "@testing-library/react";
import { ResultsTable } from "../components/ResultsTable";
import type { QueryResult } from "../api";

const result: QueryResult = {
  columns: [
    { name: "city", type: "VARCHAR" },
    { name: "population", type: "BIGINT" },
  ],
  rows: [
    ["London", 8866000],
    ["Leeds", null],
  ],
  has_more: true,
  elapsed_ms: 4.2,
  cached: false,
};

describe("ResultsTable", () => {
  it("renders headers, types and formatted cells", () => {
    render(<ResultsTable result={result} page={0} pageSize={100} onPage={() => {}} onExport={() => {}} />);
    expect(screen.getByText("city")).toBeTruthy();
    expect(screen.getByText("BIGINT")).toBeTruthy();
    expect(screen.getByText("8,866,000")).toBeTruthy();
    expect(screen.getByText("NULL")).toBeTruthy();
    expect(screen.getByText(/Rows 1 to 2/)).toBeTruthy();
    expect(screen.getByText(/4.2 ms/)).toBeTruthy();
  });

  it("pages forward and disables Previous on the first page", () => {
    const onPage = vi.fn();
    render(<ResultsTable result={result} page={0} pageSize={100} onPage={onPage} onExport={() => {}} />);
    expect((screen.getByText("Previous") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByText("Next"));
    expect(onPage).toHaveBeenCalledWith(1);
  });

  it("shows when a result came from the cache", () => {
    render(<ResultsTable result={{ ...result, cached: true, has_more: false }} page={2} pageSize={100} onPage={() => {}} onExport={() => {}} />);
    expect(screen.getByText(/served from cache/)).toBeTruthy();
    expect(screen.getByText(/Rows 201 to 202/)).toBeTruthy();
    expect((screen.getByText("Next") as HTMLButtonElement).disabled).toBe(true);
  });
});
