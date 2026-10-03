import pytest

from app.cache import LRUCache
from app.engine import QueryEngine, QueryFailed, QueryTimeout


def test_load_csv_infers_schema(engine):
    ds = engine.describe("cities")
    assert ds.row_count == 4
    assert [c.name for c in ds.columns] == ["city", "population", "area_km2"]
    assert ds.columns[1].type == "BIGINT"


def test_rejects_unsafe_dataset_name(engine, csv_path):
    with pytest.raises(ValueError):
        engine.load_csv('x"; DROP TABLE cities; --', csv_path)


def test_pagination_reports_has_more(engine):
    sql = "SELECT city FROM cities ORDER BY population DESC"
    first = engine.run(sql, limit=3)
    assert [r[0] for r in first.rows] == ["London", "Birmingham", "Leeds"]
    assert first.has_more is True

    second = engine.run(sql, limit=3, offset=3)
    assert [r[0] for r in second.rows] == ["Manchester"]
    assert second.has_more is False


def test_page_size_is_capped(engine):
    engine.max_page_size = 2
    assert len(engine.run("SELECT * FROM range(10)", limit=500).rows) == 2


def test_repeat_query_is_served_from_cache(engine):
    sql = "SELECT sum(population) FROM cities"
    assert engine.run(sql).cached is False
    again = engine.run(sql)
    assert again.cached is True
    assert again.rows == [[11391000]]


def test_upload_invalidates_cache(engine, tmp_path):
    sql = "SELECT count(*) FROM cities"
    engine.run(sql)
    bigger = tmp_path / "more.csv"
    bigger.write_text("city,population,area_km2\nYork,200000,272\n")
    engine.load_csv("cities", bigger)
    result = engine.run(sql)
    assert result.cached is False
    assert result.rows == [[1]]


def test_long_query_is_cancelled():
    eng = QueryEngine(timeout_s=0.3)
    heavy = "SELECT count(*) FROM range(1000000000) a, range(1000) b WHERE a.range % 7 = b.range"
    with pytest.raises(QueryTimeout):
        eng.run(heavy)
    # The engine is still usable afterwards.
    assert eng.run("SELECT 42").rows == [[42]]
    eng.close()


def test_cannot_read_server_files(engine, csv_path):
    with pytest.raises(QueryFailed, match="(?i)permission|disabled"):
        engine.run(f"SELECT * FROM read_csv('{csv_path}')")


def test_bad_column_is_a_clean_error(engine):
    with pytest.raises(QueryFailed, match="nope"):
        engine.run("SELECT nope FROM cities")


def test_values_are_json_safe(engine):
    row = engine.run("SELECT DATE '2026-10-02', 1.50::DECIMAL(4,2), [1, 2]").rows[0]
    assert row == ["2026-10-02", 1.5, [1, 2]]


class TestLRUCache:
    def test_evicts_least_recently_used(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # a is now most recent
        cache.put("c", 3)  # evicts b
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3

    def test_tracks_hit_rate(self):
        cache = LRUCache(capacity=4)
        cache.put("k", "v")
        cache.get("k")
        cache.get("missing")
        assert cache.stats()["hit_rate"] == 0.5

    def test_capacity_must_be_positive(self):
        with pytest.raises(ValueError):
            LRUCache(0)
