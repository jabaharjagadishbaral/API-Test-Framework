"""
Small in-memory Users REST API used as the system under test.

This is intentionally self-contained (no database, no external services)
so the whole framework can be cloned and run with nothing but Python.
"""
import re
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_FIELDS = {"name", "email", "age", "tags", "status"}
ALLOWED_STATUS = {"active", "inactive"}
RATE_LIMIT = 5          # max POST /users per window, per process
RATE_WINDOW_SECONDS = 60

# ---- "auth server" -------------------------------------------------------

USERS_AUTH = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}

TOKENS = {}  # token -> {"role": ..., "expires_at": epoch}


def _issue_token(role, ttl=3600):
    token = f"tok-{role}-{int(time.time() * 1000)}"
    TOKENS[token] = {"role": role, "expires_at": time.time() + ttl}
    return token


def _seed_tokens():
    TOKENS.clear()
    TOKENS["valid-token-admin"] = {"role": "admin", "expires_at": time.time() + 3600}
    TOKENS["valid-token-user"] = {"role": "user", "expires_at": time.time() + 3600}
    TOKENS["expired-token-789"] = {"role": "user", "expires_at": time.time() - 10}
    TOKENS["refresh-token-999"] = {"role": "user", "expires_at": time.time() + 3600, "refresh": True}


def _current_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, "missing_or_malformed"
    token = header[len("Bearer "):].strip()
    info = TOKENS.get(token)
    if info is None:
        return None, "invalid"
    if info["expires_at"] < time.time():
        return None, "expired"
    return info, None


def require_auth(role=None):
    info, err = _current_token()
    if err == "expired":
        return None, (jsonify(error="token_expired", message="Access token has expired"), 401)
    if err in ("invalid", "missing_or_malformed"):
        return None, (jsonify(error="unauthorized", message="Missing or invalid authorization header"), 401)
    if role and info["role"] != role:
        return None, (jsonify(error="forbidden", message=f"Requires role '{role}'"), 403)
    return info, None


# ---- "users" resource ------------------------------------------------------

STATE = {}


def _seed_state():
    STATE["users"] = {
        1: {"id": 1, "name": "Alice Wong", "email": "alice@example.com", "age": 29,
            "tags": [], "status": "active", "created_at": _now_iso()},
        2: {"id": 2, "name": "Bob Singh", "email": "bob@example.com", "age": 34,
            "tags": [], "status": "active", "created_at": _now_iso()},
        3: {"id": 3, "name": "Carol Diaz", "email": "carol@example.com", "age": 41,
            "tags": [], "status": "inactive", "created_at": _now_iso()},
    }
    STATE["next_id"] = 4
    STATE["post_users_timestamps"] = []


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_user_payload(data, partial=False):
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    extra = set(data.keys()) - ALLOWED_FIELDS
    if extra:
        return f"Unexpected field(s): {', '.join(sorted(extra))}"

    if not partial and "name" not in data:
        return "'name' is required"
    if not partial and "email" not in data:
        return "'email' is required"

    if "name" in data:
        if not isinstance(data["name"], str):
            return "'name' must be a string"
        if len(data["name"]) < 1:
            return "'name' must not be empty"
        if len(data["name"]) > 200:
            return "'name' must be at most 200 characters"

    if "email" in data:
        if not isinstance(data["email"], str) or not EMAIL_RE.match(data["email"]):
            return "'email' must be a valid email address"

    if "age" in data and data["age"] is not None:
        if not isinstance(data["age"], int) or isinstance(data["age"], bool):
            return "'age' must be an integer"
        if data["age"] < 0 or data["age"] > 150:
            return "'age' must be between 0 and 150"

    if "tags" in data and data["tags"] is not None:
        if not isinstance(data["tags"], list) or not all(isinstance(t, str) for t in data["tags"]):
            return "'tags' must be a list of strings"
        if len(data["tags"]) > 10:
            return "'tags' may contain at most 10 items"

    if "status" in data and data["status"] not in ALLOWED_STATUS:
        return f"'status' must be one of {sorted(ALLOWED_STATUS)}"

    return None


@app.post("/_test/reset")
def test_reset():
    """Test-only helper: restores the API to a clean, known state."""
    _seed_state()
    _seed_tokens()
    return jsonify(reset=True)


@app.post("/auth/login")
def login():
    data = request.get_json(silent=True)
    if not data or "username" not in data or "password" not in data:
        return jsonify(error="bad_request", message="username and password are required"), 400
    account = USERS_AUTH.get(data["username"])
    if not account or account["password"] != data["password"]:
        return jsonify(error="invalid_credentials", message="Username or password is incorrect"), 401
    token = _issue_token(account["role"])
    return jsonify(token=token, role=account["role"]), 200


@app.post("/auth/refresh")
def refresh():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return jsonify(error="unauthorized", message="Missing or invalid authorization header"), 401
    token = header[len("Bearer "):].strip()
    info = TOKENS.get(token)
    if not info or not info.get("refresh"):
        return jsonify(error="unauthorized", message="Not a valid refresh token"), 401
    new_token = _issue_token(info["role"])
    return jsonify(token=new_token, role=info["role"]), 200


@app.get("/admin/stats")
def admin_stats():
    _, err = require_auth(role="admin")
    if err:
        return err
    return jsonify(user_count=len(STATE["users"])), 200


@app.get("/users")
def list_users():
    _, err = require_auth()
    if err:
        return err

    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify(error="bad_request", message="limit and offset must be integers"), 400

    if limit < 0 or limit > 100:
        return jsonify(error="bad_request", message="limit must be between 0 and 100"), 400
    if offset < 0:
        return jsonify(error="bad_request", message="offset must be >= 0"), 400

    all_users = sorted(STATE["users"].values(), key=lambda u: u["id"])
    page = all_users[offset:offset + limit]
    return jsonify(users=page, total=len(all_users)), 200


@app.post("/users")
def create_user():
    _, err = require_auth()
    if err:
        return err

    now = time.time()
    STATE["post_users_timestamps"] = [t for t in STATE["post_users_timestamps"] if now - t < RATE_WINDOW_SECONDS]
    if len(STATE["post_users_timestamps"]) >= RATE_LIMIT:
        return jsonify(error="rate_limited", message="Too many requests, slow down"), 429

    if not request.is_json:
        return jsonify(error="bad_request", message="Body must be valid JSON"), 400
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="bad_request", message="Malformed JSON body"), 400

    problem = _validate_user_payload(data, partial=False)
    if problem:
        return jsonify(error="validation_error", message=problem), 400

    if any(u["email"] == data["email"] for u in STATE["users"].values()):
        return jsonify(error="conflict", message="A user with this email already exists"), 409

    user_id = STATE["next_id"]
    STATE["next_id"] += 1
    user = {
        "id": user_id,
        "name": data["name"],
        "email": data["email"],
        "age": data.get("age"),
        "tags": data.get("tags", []),
        "status": data.get("status", "active"),
        "created_at": _now_iso(),
    }
    STATE["users"][user_id] = user
    STATE["post_users_timestamps"].append(now)
    return jsonify(user), 201


@app.get("/users/<int:user_id>")
def get_user(user_id):
    _, err = require_auth()
    if err:
        return err
    user = STATE["users"].get(user_id)
    if not user:
        return jsonify(error="not_found", message=f"No user with id {user_id}"), 404
    return jsonify(user), 200


@app.put("/users/<int:user_id>")
def update_user(user_id):
    _, err = require_auth()
    if err:
        return err
    user = STATE["users"].get(user_id)
    if not user:
        return jsonify(error="not_found", message=f"No user with id {user_id}"), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="bad_request", message="Malformed JSON body"), 400

    problem = _validate_user_payload(data, partial=True)
    if problem:
        return jsonify(error="validation_error", message=problem), 400

    user.update(data)
    return jsonify(user), 200


@app.delete("/users/<int:user_id>")
def delete_user(user_id):
    _, err = require_auth(role="admin")
    if err:
        return err
    user = STATE["users"].pop(user_id, None)
    if not user:
        return jsonify(error="not_found", message=f"No user with id {user_id}"), 404
    return "", 204


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify(error="method_not_allowed", message="This HTTP method is not supported here"), 405


_seed_state()
_seed_tokens()

if __name__ == "__main__":
    app.run(port=5055)
