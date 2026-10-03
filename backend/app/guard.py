"""Read only guard for user SQL.

DuckDB's own parser splits the input into statements, so comments and
string literals cannot be used to hide a second statement.
"""

import duckdb


class QueryRejected(ValueError):
    """The SQL is not a single read only query."""


def validate_read_only(sql: str) -> str:
    """Return the single SELECT statement in `sql`, or raise QueryRejected."""
    if not sql or not sql.strip():
        raise QueryRejected("Query is empty.")

    try:
        statements = duckdb.extract_statements(sql)
    except duckdb.ParserException as exc:
        raise QueryRejected(f"Syntax error: {exc}") from exc

    if len(statements) != 1:
        raise QueryRejected("Run one statement at a time.")

    statement = statements[0]
    if statement.type != duckdb.StatementType.SELECT:
        kind = statement.type.name.replace("_", " ").lower()
        raise QueryRejected(f"Only SELECT queries are allowed, got {kind}.")

    return statement.query.strip()
