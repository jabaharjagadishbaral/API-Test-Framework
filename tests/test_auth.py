"""Authentication and authorization test cases."""


def test_valid_token_access(user_client):
    resp = user_client.get("/users")
    assert resp.status_code == 200
    assert "users" in resp.json()


def test_expired_token_rejected(client):
    client.set_token("expired-token-789")
    resp = client.get("/users")
    assert resp.status_code == 401
    assert resp.json()["error"] == "token_expired"


def test_missing_auth_header(client):
    resp = client.get("/users", skip_auth=True)
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


def test_invalid_credentials(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_credentials"


def test_refresh_token_flow(client):
    client.set_token("refresh-token-999")
    resp = client.post("/auth/refresh")
    assert resp.status_code == 200
    new_token = resp.json()["token"]
    assert new_token and new_token != "refresh-token-999"

    client.set_token(new_token)
    followup = client.get("/users")
    assert followup.status_code == 200


def test_role_based_access(user_client):
    # a non-admin token must not be able to delete users
    resp = user_client.delete("/users/1")
    assert resp.status_code == 403
    assert resp.json()["error"] == "forbidden"


def test_session_timeout(client):
    # an expired token must be rejected on write endpoints too, not just reads
    client.set_token("expired-token-789")
    resp = client.post("/users", json={"name": "Late User", "email": "late@example.com"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "token_expired"


def test_malformed_auth_header(client):
    resp = client.get("/users", headers={"Authorization": "Token abc123"}, skip_auth=True)
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"
