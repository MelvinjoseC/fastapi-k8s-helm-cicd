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


def test_security_headers_present(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in res.headers["Content-Security-Policy"]


def test_correlation_id_and_timing_headers(client):
    res = client.get("/tasks")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert "X-Process-Time-Ms" in res.headers


def test_create_task(client):
    res = client.post("/tasks", json={"title": "Write resume", "description": "Add this project"})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Write resume"
    assert body["completed"] is False
    assert body["status"] == "pending"
    assert body["priority"] == "medium"
    assert "id" in body


def test_create_task_with_priority_and_tags(client):
    res = client.post(
        "/tasks",
        json={
            "title": "Harden K8s Network Policy",
            "priority": "urgent",
            "tags": ["security", "kubernetes"],
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["priority"] == "urgent"
    assert "security" in body["tags"]
    assert "kubernetes" in body["tags"]


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
    assert res.json()["status"] == "completed"
    assert res.json()["title"] == "Original"


def test_update_missing_task_404(client):
    res = client.put("/tasks/9999", json={"completed": True})
    assert res.status_code == 404


def test_delete_task_soft_and_restore(client):
    created = client.post("/tasks", json={"title": "To delete"}).json()
    task_id = created["id"]

    # Soft delete
    res = client.delete(f"/tasks/{task_id}")
    assert res.status_code == 204

    # Standard get returns 404
    assert client.get(f"/tasks/{task_id}").status_code == 404

    # Not included in active list
    list_res = client.get("/tasks")
    assert not any(t["id"] == task_id for t in list_res.json())

    # Included if include_deleted=True
    deleted_list_res = client.get("/tasks", params={"include_deleted": True})
    assert any(t["id"] == task_id for t in deleted_list_res.json())

    # Restore task
    restore_res = client.post(f"/tasks/{task_id}/restore")
    assert restore_res.status_code == 200
    assert client.get(f"/tasks/{task_id}").status_code == 200


def test_permanent_delete(client):
    created = client.post("/tasks", json={"title": "Permanent removal"}).json()
    task_id = created["id"]
    del_res = client.delete(f"/tasks/{task_id}", params={"permanent": True})
    assert del_res.status_code == 204

    # Not even in include_deleted list
    deleted_list_res = client.get("/tasks", params={"include_deleted": True})
    assert not any(t["id"] == task_id for t in deleted_list_res.json())


def test_filter_tasks_by_completed(client):
    a = client.post("/tasks", json={"title": "A"}).json()
    client.post("/tasks", json={"title": "B"})
    client.put(f"/tasks/{a['id']}", json={"completed": True})

    res = client.get("/tasks", params={"completed": True})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "A"


def test_filter_tasks_by_priority(client):
    client.post("/tasks", json={"title": "Low priority", "priority": "low"})
    client.post("/tasks", json={"title": "Urgent priority", "priority": "urgent"})

    res = client.get("/tasks", params={"priority": "urgent"})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "Urgent priority"


def test_search_tasks_keyword(client):
    client.post("/tasks", json={"title": "Deploy with Helm", "description": "Using ArgoCD"})
    client.post("/tasks", json={"title": "Write Unit Tests", "description": "Cover all endpoints"})

    res = client.get("/tasks", params={"q": "Helm"})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "Deploy with Helm"


def test_paginated_tasks(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"Batch Task {i}"})

    res = client.get("/tasks/paginated", params={"page": 1, "page_size": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3