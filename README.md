# REST API Testing & Automation Framework

An automated test framework for REST APIs, built with **Python, PyTest, and Requests**,
with request design mirrored in a **Postman** collection. It ships with its own tiny
Flask API (an in-memory Users service) as the system under test, so the whole thing
runs with no external dependencies or accounts.

30 test cases across 5 categories exercise GET, POST, PUT, and DELETE, covering the
happy path as well as authentication, validation, boundary, and negative scenarios.

## Project structure

```
api_test_framework/
├── app.py                 # Flask API under test (users, auth, admin/stats)
├── conftest.py             # Starts the API for the test session, resets state per test
├── requirements.txt
├── pytest.ini
├── utils/
│   └── api_client.py       # Thin requests.Session wrapper used by every test
├── tests/
│   ├── test_auth.py         # 8 cases  — tokens, expiry, roles, refresh
│   ├── test_validation.py   # 7 cases  — schema, types, required fields
│   ├── test_boundary.py     # 6 cases  — lengths, limits, unicode, arrays
│   ├── test_negative.py     # 5 cases  — 404 / 409 / 403 / 405 / 429
│   └── test_regression.py   # 4 cases  — locked-in fixes for past bugs
└── postman/
    └── collection.json      # Manual/exploratory version of the same requests
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the tests

```bash
pytest
```

`conftest.py` starts the Flask app on `127.0.0.1:5055` once per test session and
resets its in-memory data before every single test, so tests can run in any order
and never leak state into each other.

Run one category at a time:

```bash
pytest tests/test_auth.py
pytest tests/test_validation.py -k oversized
```

## The API under test

| Method | Path              | Notes                                   |
|--------|-------------------|------------------------------------------|
| POST   | `/auth/login`     | `{username, password}` → `{token, role}` |
| POST   | `/auth/refresh`   | Bearer refresh token → new token         |
| GET    | `/users`          | `?limit=&offset=`, requires auth         |
| POST   | `/users`          | Create user, rate-limited (5/min)        |
| GET    | `/users/<id>`     | 404 if missing                           |
| PUT    | `/users/<id>`     | Partial update                           |
| DELETE | `/users/<id>`     | Admin role only                          |
| GET    | `/admin/stats`    | Admin role only                          |

Seeded accounts: `admin / admin123` (admin role) and `user / user123` (user role).
Fixed tokens `valid-token-admin`, `valid-token-user`, and `expired-token-789` are
also available for tests that need a token without a login round trip.

## What each category actually checks

- **Auth (8):** valid/expired/missing/malformed tokens, invalid login, refresh flow,
  role-gated delete, expired token on a write endpoint.
- **Validation (7):** required fields, wrong types, oversized strings, invalid enum
  values, malformed JSON, and rejection of unexpected extra fields.
- **Boundary (6):** max-length strings, empty strings, zero/negative numbers,
  pagination edges, unicode input, max array size.
- **Negative (5):** 404 on missing resource, 409 on duplicate email, 403 on a
  forbidden admin route, 405 on an unsupported method, 429 on rate limiting.
- **Regression (4):** pagination offset slicing, non-reused IDs after delete,
  ISO-8601 timestamp formatting, deleted rows not lingering in listings.

## Extending it

- Point `conftest.py`'s `BASE_URL` at a real staging API instead of the bundled
  Flask app — the tests themselves don't care where the server lives.
- Add new cases by dropping another `test_*.py` file in `tests/`; the `client`,
  `admin_client`, and `user_client` fixtures are already wired up with auth.
