def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ready(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_metrics_exposed(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "http_requests_total" in res.text


def test_create_task(client):
    res = client.post("/tasks", json={"title": "Write resume", "description": "Add this project"})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Write resume"
    assert body["completed"] is False
    assert "id" in body


def test_create_task_requires_title(client):
    res = client.post("/tasks", json={"description": "missing title"})
    assert res.status_code == 422


def test_list_tasks(client):
    client.post("/tasks", json={"title": "Task A"})
    client.post("/tasks", json={"title": "Task B"})
    res = client.get("/tasks")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_task(client):
    created = client.post("/tasks", json={"title": "Solo task"}).json()
    res = client.get(f"/tasks/{created['id']}")
    assert res.status_code == 200
    assert res.json()["title"] == "Solo task"


def test_get_missing_task_404(client):
    res = client.get("/tasks/9999")
    assert res.status_code == 404


def test_update_task(client):
    created = client.post("/tasks", json={"title": "Original"}).json()
    res = client.put(f"/tasks/{created['id']}", json={"completed": True})
    assert res.status_code == 200
    assert res.json()["completed"] is True
    assert res.json()["title"] == "Original"


def test_update_missing_task_404(client):
    res = client.put("/tasks/9999", json={"completed": True})
    assert res.status_code == 404


def test_delete_task(client):
    created = client.post("/tasks", json={"title": "To delete"}).json()
    res = client.delete(f"/tasks/{created['id']}")
    assert res.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_filter_tasks_by_completed(client):
    a = client.post("/tasks", json={"title": "A"}).json()
    client.post("/tasks", json={"title": "B"})
    client.put(f"/tasks/{a['id']}", json={"completed": True})

    res = client.get("/tasks", params={"completed": True})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "A"
