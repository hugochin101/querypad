import os

os.environ["QUERYPAD_AUTOSTART"] = "0"

import pytest
from fastapi.testclient import TestClient

from app.engine import QueryEngine
from app.main import create_app
from app.store import MetadataStore

CSV = "city,population,area_km2\nLondon,8866000,1572\nManchester,568000,116\nBirmingham,1145000,268\nLeeds,812000,552\n"


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "cities.csv"
    path.write_text(CSV)
    return path


@pytest.fixture
def engine(csv_path):
    eng = QueryEngine(timeout_s=2.0)
    eng.load_csv("cities", csv_path)
    yield eng
    eng.close()


@pytest.fixture
def store():
    s = MetadataStore()
    yield s
    s.close()


@pytest.fixture
def client(engine, store):
    return TestClient(create_app(engine, store))
