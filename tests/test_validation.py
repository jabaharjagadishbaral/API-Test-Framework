"""Input validation test cases for POST/PUT /users."""


def test_schema_conformance(user_client):
    payload = {"name": "Dana Lee", "email": "dana@example.com", "age": 27}
    resp = user_client.post("/users", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    for field in ("id", "name", "email", "age", "status", "created_at"):
        assert field in body


def test_missing_required_field(user_client):
    resp = user_client.post("/users", json={"name": "No Email"})
    assert resp.status_code == 400
    assert "email" in resp.json()["message"]


def test_wrong_data_type(user_client):
    resp = user_client.post("/users", json={
        "name": "Type Error", "email": "type@example.com", "age": "thirty",
    })
    assert resp.status_code == 400
    assert "age" in resp.json()["message"]


def test_oversized_payload(user_client):
    resp = user_client.post("/users", json={
        "name": "X" * 500, "email": "oversized@example.com",
    })
    assert resp.status_code == 400
    assert "200 characters" in resp.json()["message"]


def test_invalid_enum_value(user_client):
    resp = user_client.post("/users", json={
        "name": "Enum Test", "email": "enum@example.com", "status": "pending",
    })
    assert resp.status_code == 400
    assert "status" in resp.json()["message"]


def test_malformed_json_body(user_client):
    resp = user_client.post(
        "/users",
        data="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_unexpected_extra_fields(user_client):
    resp = user_client.post("/users", json={
        "name": "Sneaky", "email": "sneaky@example.com", "is_admin": True,
    })
    assert resp.status_code == 400
    assert "is_admin" in resp.json()["message"]
