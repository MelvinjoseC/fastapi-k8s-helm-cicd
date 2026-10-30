"""Integration tests for Task API bulk operations."""


def test_bulk_create_tasks(client):
    payload = {
        "tasks": [
            {"title": "Bulk Task 1", "priority": "low"},
            {"title": "Bulk Task 2", "priority": "medium", "tags": ["bulk", "test"]},
            {"title": "Bulk Task 3", "priority": "urgent", "estimated_hours": 3.0},
        ]
    }
    response = client.post("/tasks/bulk", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["created_count"] == 3
    assert len(data["tasks"]) == 3
    assert data["tasks"][0]["title"] == "Bulk Task 1"


def test_bulk_update_tasks(client):
    # First create two tasks
    r1 = client.post("/tasks", json={"title": "To Update 1"})
    r2 = client.post("/tasks", json={"title": "To Update 2"})
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Bulk update to completed
    update_payload = {
        "task_ids": [id1, id2],
        "completed": True,
        "priority": "high",
    }
    patch_resp = client.patch("/tasks/bulk", json=update_payload)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["affected_count"] == 2

    # Verify updated values
    get1 = client.get(f"/tasks/{id1}").json()
    get2 = client.get(f"/tasks/{id2}").json()
    assert get1["completed"] is True
    assert get1["priority"] == "high"
    assert get2["completed"] is True


def test_bulk_delete_tasks(client):
    # Create two tasks
    r1 = client.post("/tasks", json={"title": "To Delete 1"})
    r2 = client.post("/tasks", json={"title": "To Delete 2"})
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Bulk soft delete
    del_payload = {"task_ids": [id1, id2], "permanent": False}
    del_resp = client.request("DELETE", "/tasks/bulk", json=del_payload)
    assert del_resp.status_code == 200
    assert del_resp.json()["affected_count"] == 2

    # Verify they are no longer in active task list
    list_resp = client.get("/tasks")
    active_ids = [t["id"] for t in list_resp.json()]
    assert id1 not in active_ids
    assert id2 not in active_ids
