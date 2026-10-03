import pytest

from app.guard import QueryRejected, validate_read_only


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select * from cities where population > 1000000",
        "WITH big AS (SELECT * FROM cities) SELECT count(*) FROM big",
        "SELECT 1;",
        "-- a comment\nSELECT 'drop table cities'",
    ],
)
def test_accepts_single_select(sql):
    assert validate_read_only(sql).lower().lstrip().startswith(("select", "with", "--"))


@pytest.mark.parametrize(
    "sql, message",
    [
        ("DROP TABLE cities", "drop"),
        ("INSERT INTO cities VALUES ('York', 1, 1)", "insert"),
        ("UPDATE cities SET population = 0", "update"),
        ("DELETE FROM cities", "delete"),
        ("CREATE TABLE x AS SELECT 1", "create"),
        ("COPY cities TO 'out.csv'", "copy"),
        ("ATTACH 'other.db'", "attach"),
        ("SET threads = 1", "set"),
    ],
)
def test_rejects_writes_and_side_effects(sql, message):
    with pytest.raises(QueryRejected, match=message):
        validate_read_only(sql)


def test_rejects_stacked_statements():
    with pytest.raises(QueryRejected, match="one statement"):
        validate_read_only("SELECT 1; DROP TABLE cities")


def test_rejects_empty_and_invalid():
    with pytest.raises(QueryRejected, match="empty"):
        validate_read_only("   ")
    with pytest.raises(QueryRejected, match="Syntax"):
        validate_read_only("SELEC 1")
