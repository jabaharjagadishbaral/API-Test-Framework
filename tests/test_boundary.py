"""Boundary condition test cases."""


def test_max_length_string(user_client):
    resp = user_client.post("/users", json={
        "name": "N" * 200, "email": "maxlen@example.com",
    })
    assert resp.status_code == 201


def test_empty_string_field(user_client):
    resp = user_client.post("/users", json={"name": "", "email": "empty@example.com"})
    assert resp.status_code == 400


def test_zero_and_negative_values(user_client):
    zero_age = user_client.post("/users", json={
        "name": "Newborn", "email": "newborn@example.com", "age": 0,
    })
    assert zero_age.status_code == 201  # zero is a valid age

    negative_age = user_client.post("/users", json={
        "name": "Impossible", "email": "impossible@example.com", "age": -5,
    })
    assert negative_age.status_code == 400


def test_pagination_limit_edge(user_client):
    empty_page = user_client.get("/users", params={"limit": 0})
    assert empty_page.status_code == 200
    assert empty_page.json()["users"] == []

    too_large = user_client.get("/users", params={"limit": 1000})
    assert too_large.status_code == 400


def test_unicode_special_chars(user_client):
    resp = user_client.post("/users", json={
        "name": "José Müller 🚀", "email": "jose@example.com",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "José Müller 🚀"


def test_max_array_size(user_client):
    ok = user_client.post("/users", json={
        "name": "Tagged", "email": "tagged@example.com", "tags": [f"t{i}" for i in range(10)],
    })
    assert ok.status_code == 201

    too_many = user_client.post("/users", json={
        "name": "Overtagged", "email": "overtagged@example.com", "tags": [f"t{i}" for i in range(11)],
    })
    assert too_many.status_code == 400
