"""Generate a synthetic bike hire dataset for demos and benchmarks.

Usage: python scripts/make_sample_data.py [rows] [out.csv]
"""

import sys

import duckdb

STATIONS = [
    "Waterloo", "King's Cross", "Liverpool Street", "Hyde Park Corner",
    "London Bridge", "Paddington", "Victoria", "Canary Wharf",
    "Shoreditch", "South Bank", "Camden Town", "Euston",
]


def main(rows: int = 500_000, out: str = "data/bike_trips.csv") -> None:
    con = duckdb.connect()
    con.execute("SELECT setseed(0.42)")
    stations = "[" + ", ".join("'" + s.replace("'", "''") + "'" for s in STATIONS) + "]"
    con.execute(f"""
        COPY (
            SELECT
                i AS trip_id,
                TIMESTAMP '2026-01-01' + to_seconds(CAST(random() * 86400 * 270 AS BIGINT)) AS started_at,
                list_extract({stations}, 1 + CAST(floor(random() * {len(STATIONS)}) AS INT)) AS start_station,
                list_extract({stations}, 1 + CAST(floor(random() * {len(STATIONS)}) AS INT)) AS end_station,
                CAST(3 + random() * 55 AS INT) AS duration_min,
                CASE WHEN random() < 0.18 THEN 'e-bike' ELSE 'classic' END AS bike_type,
                CASE WHEN random() < 0.62 THEN 'member' ELSE 'casual' END AS rider_type
            FROM range(1, {rows} + 1) t(i)
        ) TO '{out}' (HEADER, DELIMITER ',')
    """)
    print(f"Wrote {rows:,} rows to {out}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000
    path = sys.argv[2] if len(sys.argv) > 2 else "data/bike_trips.csv"
    main(n, path)
