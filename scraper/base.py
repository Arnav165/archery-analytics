import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://www.worldarchery.sport"

# Used only for plain JSON/API requests that don't need JS rendering
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}


class BaseScraper:
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self._pw = None
        self._browser = None
        self._page = None
        # Fallback session for raw JSON endpoints
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)

    # ------------------------------------------------------------------
    # Playwright lifecycle
    # ------------------------------------------------------------------

    def _ensure_browser(self):
        if self._browser is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            context = self._browser.new_context(
                user_agent=_HEADERS["User-Agent"],
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            self._page = context.new_page()
            # Block images/fonts to speed up scraping
            self._page.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf}",
                lambda route: route.abort(),
            )

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._pw = None
        self._page = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Core fetch — Playwright renders JS, then BeautifulSoup parses HTML
    # ------------------------------------------------------------------

    def get(self, url: str, wait_selector: str = "body", wait_ms: int = 3000) -> BeautifulSoup | None:
        self._ensure_browser()
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for a key selector or a fixed settle time
            try:
                self._page.wait_for_selector(wait_selector, timeout=wait_ms)
            except PWTimeout:
                pass  # settle time elapsed — parse whatever loaded
            time.sleep(self.delay)
            html = self._page.content()
            return BeautifulSoup(html, "lxml")
        except PWTimeout:
            print(f"[WARN] Timed out loading {url}")
            return None
        except Exception as e:
            print(f"[WARN] Failed to fetch {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # JSON fetch — plain requests (no JS needed for API endpoints)
    # ------------------------------------------------------------------

    def get_json(self, url: str) -> dict | list | None:
        try:
            resp = self._session.get(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            time.sleep(self.delay)
            return resp.json()
        except Exception as e:
            print(f"[WARN] Failed to fetch JSON {url}: {e}")
            return None
