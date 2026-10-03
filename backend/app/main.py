"""HTTP API for QueryPad."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import QueryEngine, QueryFailed, QueryTimeout
from .guard import QueryRejected, validate_read_only
from .store import DuplicateName, MetadataStore

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class QueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SaveQueryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sql: str = Field(min_length=1, max_length=20_000)


def create_app(engine: QueryEngine, store: MetadataStore, static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="QueryPad", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("QUERYPAD_CORS", "http://localhost:5173").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "cache": engine.cache.stats()}

    # Datasets

    @app.get("/api/datasets")
    def list_datasets():
        return engine.list_datasets()

    @app.post("/api/datasets", status_code=status.HTTP_201_CREATED)
    async def upload_dataset(name: str = Form(...), file: UploadFile = File(...)):
        if not (file.filename or "").lower().endswith(".csv"):
            raise HTTPException(400, "Upload a .csv file.")
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    tmp.close()
                    os.unlink(tmp.name)
                    raise HTTPException(413, "File is larger than 50 MB.")
                tmp.write(chunk)
        try:
            return await run_in_threadpool(engine.load_csv, name, tmp.name)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        finally:
            os.unlink(tmp.name)

    @app.delete("/api/datasets/{name}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_dataset(name: str):
        try:
            engine.drop(name)
        except KeyError:
            raise HTTPException(404, f"No dataset named {name}.")

    # Queries

    @app.post("/api/query")
    async def run_query(req: QueryRequest):
        try:
            result = await run_in_threadpool(engine.run, req.sql, req.limit, req.offset)
        except QueryRejected as exc:
            store.record_run(req.sql, "rejected", error=str(exc))
            raise HTTPException(400, str(exc)) from exc
        except QueryTimeout as exc:
            store.record_run(req.sql, "timeout", error=str(exc))
            raise HTTPException(408, str(exc)) from exc
        except QueryFailed as exc:
            store.record_run(req.sql, "error", error=str(exc))
            raise HTTPException(400, str(exc)) from exc
        store.record_run(req.sql, "ok", result.elapsed_ms, len(result.rows))
        return result

    @app.get("/api/history")
    def history(limit: int = 50):
        return store.history(max(1, min(limit, 200)))

    # Saved queries

    @app.get("/api/saved-queries")
    def list_saved():
        return store.list_queries()

    @app.post("/api/saved-queries", status_code=status.HTTP_201_CREATED)
    def save(req: SaveQueryRequest):
        try:
            validate_read_only(req.sql)
        except QueryRejected as exc:
            raise HTTPException(400, str(exc)) from exc
        try:
            return store.save_query(req.name, req.sql)
        except DuplicateName:
            raise HTTPException(409, f"A saved query named {req.name!r} already exists.")

    @app.delete("/api/saved-queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_saved(query_id: int):
        if not store.delete_query(query_id):
            raise HTTPException(404, "Saved query not found.")

    if static_dir and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


def _default_app() -> FastAPI:
    data_dir = Path(os.getenv("QUERYPAD_DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = QueryEngine(
        data_dir / "querypad.duckdb",
        timeout_s=float(os.getenv("QUERYPAD_TIMEOUT_S", "5")),
    )
    store = MetadataStore(data_dir / "metadata.sqlite")

    seed = os.getenv("QUERYPAD_SEED_CSV")
    if seed and Path(seed).exists() and not engine.list_datasets():
        engine.load_csv(Path(seed).stem, seed)

    static = os.getenv("QUERYPAD_STATIC_DIR")
    return create_app(engine, store, Path(static) if static else None)


app = _default_app() if os.getenv("QUERYPAD_AUTOSTART", "1") == "1" else None
