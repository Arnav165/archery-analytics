import time
import requests

BASE = "https://api.worldarchery.org/v4/API"

_HEADERS = {
    "User-Agent": "archery-analytics/1.0",
    "Accept": "application/json",
}


class WAClient:
    """Thin wrapper around the World Archery REST API v4."""

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """Fetch a single page from the API. Returns the parsed JSON dict."""
        url = f"{BASE}/{endpoint}"
        try:
            resp = self._session.get(url, params=params or {}, timeout=20)
            resp.raise_for_status()
            time.sleep(self.delay)
            return resp.json()
        except requests.HTTPError as e:
            print(f"[WARN] HTTP {e.response.status_code} — {url} params={params}")
            return {}
        except Exception as e:
            print(f"[WARN] {e} — {url}")
            return {}

    def get_all(self, endpoint: str, params: dict | None = None, page_size: int = 100) -> list[dict]:
        """
        Auto-paginate through all results for an endpoint.
        Returns the flat list of all items across every page.
        """
        params = dict(params or {})
        params["RBP"] = page_size
        params["Page"] = 0

        all_items: list[dict] = []

        while True:
            data = self.get(endpoint, params)
            items = data.get("items", [])
            all_items.extend(items)

            page_info = data.get("pageInfo", {})
            total = page_info.get("totalResults", 0)

            if not items or len(all_items) >= total:
                break

            params["Page"] += 1

        return all_items
