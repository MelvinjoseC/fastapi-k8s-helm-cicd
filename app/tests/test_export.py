"""Tests for CSV and JSON data export endpoint."""

import csv
import io


def test_export_tasks_json(client):
    client.post("/tasks", json={"title": "Export JSON Task", "priority": "high"})
    response = client.get("/tasks/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "attachment; filename=\"tasks.json\"" in response.headers["content-disposition"]
    data = response.json()
    assert isinstance(data, list)
    assert any(t["title"] == "Export JSON Task" for t in data)


def test_export_tasks_csv(client):
    client.post(
        "/tasks",
        json={"title": "Export CSV Task", "priority": "urgent", "tags": ["export", "csv"]},
    )
    response = client.get("/tasks/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=\"tasks.csv\"" in response.headers["content-disposition"]

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) >= 1
    assert "id" in reader.fieldnames
    assert "title" in reader.fieldnames
    assert any(r["title"] == "Export CSV Task" for r in rows)


def test_export_tasks_invalid_format(client):
    response = client.get("/tasks/export?format=xml")
    assert response.status_code == 422
