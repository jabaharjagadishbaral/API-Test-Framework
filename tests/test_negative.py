"""Negative-path test cases: things that should fail, on purpose."""


def test_resource_not_found_404(user_client):
    resp = user_client.get("/users/9999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


def test_duplicate_creation_409(user_client):
    payload = {"name": "Dup One", "email": "dup@example.com"}
    first = user_client.post("/users", json=payload)
    assert first.status_code == 201

    second = user_client.post("/users", json={"name": "Dup Two", "email": "dup@example.com"})
    assert second.status_code == 409
    assert second.json()["error"] == "conflict"


def test_unauthorized_access_403(user_client):
    resp = user_client.get("/admin/stats")
    assert resp.status_code == 403
    assert resp.json()["error"] == "forbidden"


def test_invalid_method_405(user_client):
    resp = user_client.patch("/users/1", json={"name": "Patched"})
    assert resp.status_code == 405


def test_rate_limit_429(user_client):
    statuses = []
    for i in range(6):
        resp = user_client.post("/users", json={
            "name": f"Bulk {i}", "email": f"bulk{i}@example.com",
        })
        statuses.append(resp.status_code)

    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429
