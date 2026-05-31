import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.worldarchery.sport"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class BaseScraper:
    def __init__(self, delay: float = 1.5):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    def get(self, url: str) -> BeautifulSoup | None:
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            print(f"[WARN] Failed to fetch {url}: {e}")
            return None

    def get_json(self, url: str) -> dict | list | None:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            time.sleep(self.delay)
            return resp.json()
        except Exception as e:
            print(f"[WARN] Failed to fetch JSON {url}: {e}")
            return None
