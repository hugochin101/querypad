"""Query engine: owns the DuckDB database, runs guarded queries, ingests CSVs."""

from __future__ import annotations

import datetime as dt
import decimal
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from .cache import LRUCache
from .guard import validate_read_only

TABLE_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class QueryTimeout(RuntimeError):
    """The query ran past the time limit and was cancelled."""


class QueryFailed(RuntimeError):
    """DuckDB raised an error while running the query."""


@dataclass
class Column:
    name: str
    type: str


@dataclass
class QueryResult:
    columns: list[Column]
    rows: list[list]
    has_more: bool
    elapsed_ms: float
    cached: bool = False


@dataclass
class Dataset:
    name: str
    row_count: int
    columns: list[Column] = field(default_factory=list)


def _json_safe(value):
    """DuckDB returns dates, decimals and UUIDs; JSON needs plain values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (dt.date, dt.datetime, dt.time, uuid.UUID, dt.timedelta)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return str(value)


class QueryEngine:
    """Runs read only SQL against uploaded datasets.

    User queries run on a database opened with external access disabled, so
    a SELECT cannot read files on the server through read_csv() and similar
    functions. CSV uploads are parsed by a separate in memory connection and
    copied across as a DataFrame.
    """

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        timeout_s: float = 5.0,
        max_page_size: int = 1000,
        cache_capacity: int = 128,
    ):
        self.timeout_s = timeout_s
        self.max_page_size = max_page_size
        self._db = duckdb.connect(str(db_path), config={"enable_external_access": False})
        self._write_lock = threading.Lock()
        self._version = 0
        self.cache = LRUCache(cache_capacity)

    # Datasets

    def load_csv(self, name: str, csv_path: str | Path) -> Dataset:
        if not TABLE_NAME.match(name):
            raise ValueError(
                "Dataset name must start with a letter or underscore and use only "
                "lowercase letters, digits and underscores."
            )
        reader = duckdb.connect()
        try:
            frame = reader.read_csv(str(csv_path)).df()
        except duckdb.Error as exc:
            raise ValueError(f"Could not parse CSV: {exc}") from exc
        finally:
            reader.close()

        with self._write_lock:
            cur = self._db.cursor()
            cur.register("_upload", frame)
            try:
                cur.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _upload')
            finally:
                cur.unregister("_upload")
            # Cached results may describe the old table.
            self._version += 1
            self.cache.clear()
        return self.describe(name)

    def describe(self, name: str) -> Dataset:
        cur = self._db.cursor()
        cols = cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [name],
        ).fetchall()
        if not cols:
            raise KeyError(name)
        (count,) = cur.execute(f'SELECT count(*) FROM "{name}"').fetchone()
        return Dataset(name=name, row_count=count, columns=[Column(n, t) for n, t in cols])

    def list_datasets(self) -> list[Dataset]:
        names = self._db.cursor().execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        return [self.describe(n) for (n,) in names]

    def drop(self, name: str) -> None:
        if not TABLE_NAME.match(name):
            raise KeyError(name)
        with self._write_lock:
            self.describe(name)  # raises KeyError if missing
            self._db.cursor().execute(f'DROP TABLE "{name}"')
            self._version += 1
            self.cache.clear()

    # Queries

    def run(self, sql: str, limit: int = 100, offset: int = 0) -> QueryResult:
        query = validate_read_only(sql)
        limit = max(1, min(limit, self.max_page_size))
        offset = max(0, offset)

        key = (self._version, query, limit, offset)
        hit = self.cache.get(key)
        if hit is not None:
            return QueryResult(hit.columns, hit.rows, hit.has_more, 0.0, cached=True)

        # Fetch one extra row to learn whether another page exists, without
        # paying for a full COUNT(*) over the user's query.
        paged = f"SELECT * FROM ({query}) AS q LIMIT {limit + 1} OFFSET {offset}"

        cur = self._db.cursor()
        timer = threading.Timer(self.timeout_s, cur.interrupt)
        started = time.perf_counter()
        timer.start()
        try:
            cur.execute(paged)
            raw = cur.fetchall()
            description = cur.description
        except duckdb.InterruptException as exc:
            raise QueryTimeout(f"Query cancelled after {self.timeout_s:g}s.") from exc
        except duckdb.Error as exc:
            raise QueryFailed(str(exc).split("\n")[0]) from exc
        finally:
            timer.cancel()
            cur.close()
        elapsed_ms = (time.perf_counter() - started) * 1000

        columns = [Column(d[0], str(d[1])) for d in description]
        rows = [[_json_safe(v) for v in row] for row in raw[:limit]]
        result = QueryResult(columns, rows, len(raw) > limit, round(elapsed_ms, 2))
        self.cache.put(key, result)
        return result

    def close(self) -> None:
        self._db.close()
