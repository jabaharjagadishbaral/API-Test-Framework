import threading
import time

import pytest
import requests
from werkzeug.serving import make_server

from app import app as flask_app
from utils.api_client import ApiClient

HOST = "127.0.0.1"
PORT = 5055
BASE_URL = f"http://{HOST}:{PORT}"


class _ServerThread(threading.Thread):
    """Runs the Flask app in a background thread for the whole test session."""

    def __init__(self):
        super().__init__(daemon=True)
        self.server = make_server(HOST, PORT, flask_app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


@pytest.fixture(scope="session", autouse=True)
def live_server():
    thread = _ServerThread()
    thread.start()

    for _ in range(50):
        try:
            requests.get(BASE_URL + "/admin/stats", timeout=0.2)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)

    yield BASE_URL
    thread.shutdown()


@pytest.fixture(autouse=True)
def reset_state(live_server):
    """Restores the API to a known, clean state before every single test."""
    requests.post(live_server + "/_test/reset", timeout=2)
    yield


@pytest.fixture
def client(live_server):
    return ApiClient(live_server)


@pytest.fixture
def admin_client(live_server):
    c = ApiClient(live_server)
    c.set_token("valid-token-admin")
    return c


@pytest.fixture
def user_client(live_server):
    c = ApiClient(live_server)
    c.set_token("valid-token-user")
    return c
