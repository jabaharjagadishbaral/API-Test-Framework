"""
Regression cases.

Each of these locks in the fix for a bug that was found once already —
if one of these fails, something that used to work has broken again.
"""
import re

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def test_pagination_offset_bug(user_client):
    # Bug: offset used to be applied after limit instead of before it,
    # so page 2 could repeat rows from page 1.
    page1 = user_client.get("/users", params={"limit": 2, "offset": 0}).json()["users"]
    page2 = user_client.get("/users", params={"limit": 2, "offset": 2}).json()["users"]
    ids_page1 = {u["id"] for u in page1}
    ids_page2 = {u["id"] for u in page2}
    assert ids_page1.isdisjoint(ids_page2)


def test_id_not_reused_after_delete(admin_client, user_client):
    created = user_client.post("/users", json={"name": "Temp", "email": "temp@example.com"}).json()
    temp_id = created["id"]

    admin_client.delete(f"/users/{temp_id}")

    recreated = user_client.post("/users", json={"name": "Temp Again", "email": "temp2@example.com"}).json()
    assert recreated["id"] > temp_id  # ids must never be recycled


def test_created_at_iso_format(user_client):
    # Bug: created_at used to serialize as a Python repr string, not ISO 8601.
    resp = user_client.post("/users", json={"name": "Dated", "email": "dated@example.com"})
    assert resp.status_code == 201
    assert ISO_RE.match(resp.json()["created_at"])


def test_deleted_user_fully_removed_from_listing(admin_client, user_client):
    # Bug: a deleted user used to still show up in GET /users (count was
    # decremented but the row itself lingered in the in-memory store).
    created = user_client.post("/users", json={"name": "Ghost", "email": "ghost@example.com"}).json()
    ghost_id = created["id"]

    before = user_client.get("/users", params={"limit": 100}).json()
    assert any(u["id"] == ghost_id for u in before["users"])

    admin_client.delete(f"/users/{ghost_id}")

    after = user_client.get("/users", params={"limit": 100}).json()
    assert all(u["id"] != ghost_id for u in after["users"])
