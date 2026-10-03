def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"


def test_lists_datasets(client):
    data = client.get("/api/datasets").json()
    assert data[0]["name"] == "cities"
    assert data[0]["row_count"] == 4


def test_upload_csv(client):
    res = client.post(
        "/api/datasets",
        data={"name": "teams"},
        files={"file": ("teams.csv", b"team,points\nArsenal,89\nChelsea,63\n", "text/csv")},
    )
    assert res.status_code == 201
    assert res.json()["row_count"] == 2
    names = [d["name"] for d in client.get("/api/datasets").json()]
    assert names == ["cities", "teams"]


def test_upload_rejects_non_csv(client):
    res = client.post("/api/datasets", data={"name": "x"}, files={"file": ("x.json", b"{}")})
    assert res.status_code == 400


def test_delete_dataset(client):
    assert client.delete("/api/datasets/cities").status_code == 204
    assert client.delete("/api/datasets/cities").status_code == 404


def test_run_query(client):
    res = client.post("/api/query", json={"sql": "SELECT city FROM cities ORDER BY city", "limit": 2})
    body = res.json()
    assert res.status_code == 200
    assert body["columns"][0]["name"] == "city"
    assert body["rows"] == [["Birmingham"], ["Leeds"]]
    assert body["has_more"] is True


def test_write_query_is_rejected_and_logged(client):
    res = client.post("/api/query", json={"sql": "DROP TABLE cities"})
    assert res.status_code == 400
    assert "Only SELECT" in res.json()["detail"]
    assert client.get("/api/history").json()[0]["status"] == "rejected"


def test_history_records_successful_runs(client):
    client.post("/api/query", json={"sql": "SELECT 1"})
    run = client.get("/api/history").json()[0]
    assert run["status"] == "ok"
    assert run["row_count"] == 1


def test_saved_queries_crud(client):
    created = client.post("/api/saved-queries", json={"name": "Biggest", "sql": "SELECT max(population) FROM cities"})
    assert created.status_code == 201
    qid = created.json()["id"]

    dup = client.post("/api/saved-queries", json={"name": "Biggest", "sql": "SELECT 1"})
    assert dup.status_code == 409

    assert [q["name"] for q in client.get("/api/saved-queries").json()] == ["Biggest"]
    assert client.delete(f"/api/saved-queries/{qid}").status_code == 204
    assert client.get("/api/saved-queries").json() == []


def test_cannot_save_a_write_query(client):
    res = client.post("/api/saved-queries", json={"name": "bad", "sql": "DELETE FROM cities"})
    assert res.status_code == 400
