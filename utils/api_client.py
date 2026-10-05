import requests


class ApiClient:
    """Small convenience wrapper around requests.Session for the Users API."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._token = None

    def set_token(self, token):
        self._token = token

    def _headers(self, extra_headers=None, skip_auth=False):
        headers = {}
        if self._token and not skip_auth:
            headers["Authorization"] = f"Bearer {self._token}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def get(self, path, params=None, headers=None, skip_auth=False):
        return self.session.get(
            self.base_url + path, params=params,
            headers=self._headers(headers, skip_auth), timeout=5,
        )

    def post(self, path, json=None, data=None, headers=None, skip_auth=False):
        return self.session.post(
            self.base_url + path, json=json, data=data,
            headers=self._headers(headers, skip_auth), timeout=5,
        )

    def put(self, path, json=None, headers=None, skip_auth=False):
        return self.session.put(
            self.base_url + path, json=json,
            headers=self._headers(headers, skip_auth), timeout=5,
        )

    def delete(self, path, headers=None, skip_auth=False):
        return self.session.delete(
            self.base_url + path,
            headers=self._headers(headers, skip_auth), timeout=5,
        )

    def patch(self, path, json=None, headers=None, skip_auth=False):
        return self.session.patch(
            self.base_url + path, json=json,
            headers=self._headers(headers, skip_auth), timeout=5,
        )
