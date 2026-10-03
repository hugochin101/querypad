"""Load test for the query API.

Run against a server seeded with bike_trips (see README):
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 50 -r 10 -t 60s --csv loadtest/results

Half the traffic repeats a few dashboard style queries (cache friendly), half
uses a random station and duration filter so most of it misses the cache.
"""

import random

from locust import HttpUser, between, task

STATIONS = [
    "Waterloo", "King''s Cross", "Liverpool Street", "Hyde Park Corner",
    "London Bridge", "Paddington", "Victoria", "Canary Wharf",
    "Shoreditch", "South Bank", "Camden Town", "Euston",
]

DASHBOARD = [
    "SELECT start_station, count(*) AS trips FROM bike_trips GROUP BY 1 ORDER BY 2 DESC",
    "SELECT bike_type, rider_type, round(avg(duration_min), 2) AS avg_min FROM bike_trips GROUP BY ALL",
    "SELECT date_trunc('month', started_at) AS month, count(*) FROM bike_trips GROUP BY 1 ORDER BY 1",
]


class AnalystUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(1)
    def dashboard_query(self):
        self.client.post("/api/query", json={"sql": random.choice(DASHBOARD)}, name="query: dashboard")

    @task(1)
    def ad_hoc_query(self):
        station = random.choice(STATIONS)
        minutes = random.randint(5, 55)
        sql = (
            "SELECT end_station, count(*) AS trips, round(avg(duration_min), 1) AS avg_min "
            f"FROM bike_trips WHERE start_station = '{station}' AND duration_min > {minutes} "
            "GROUP BY 1 ORDER BY 2 DESC"
        )
        self.client.post("/api/query", json={"sql": sql}, name="query: ad hoc")
