"""Unit and integration tests for task analytics endpoint."""

from datetime import UTC, datetime, timedelta


def test_task_analytics_empty_database(client):
    response = client.get("/tasks/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 0
    assert data["active_tasks"] == 0
    assert data["completed_tasks"] == 0
    assert data["overdue_tasks"] == 0
    assert data["completion_rate_percent"] == 0.0


def test_task_analytics_with_data(client):
    # Create 3 tasks: 1 completed, 1 pending, 1 overdue
    now = datetime.now(UTC)
    overdue_date = (now - timedelta(days=2)).isoformat()
    future_date = (now + timedelta(days=5)).isoformat()

    client.post("/tasks", json={"title": "T1", "priority": "high", "due_date": future_date})
    client.post("/tasks", json={"title": "T2", "priority": "low", "due_date": overdue_date})
    t3 = client.post("/tasks", json={"title": "T3", "priority": "urgent"}).json()
    client.put(f"/tasks/{t3['id']}", json={"completed": True})

    response = client.get("/tasks/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 3
    assert data["completed_tasks"] == 1
    assert data["active_tasks"] == 2
    assert data["overdue_tasks"] == 1
    assert data["completion_rate_percent"] == 33.33
    assert "urgent" in data["priority_distribution"]
    assert "high" in data["priority_distribution"]
