import json
import re
from .base import BaseScraper, BASE_URL


class TournamentScraper(BaseScraper):
    """Scrapes tournament results from www.worldarchery.sport."""

    # Known high-value competition IDs to seed scraping
    SEED_IDS = [
        24448,  # 2025 World Archery Championships
        23176,  # 2024 Paris Olympics
        24347,  # 2024 Paralympics
        22900,  # 2023 World Archery Championships
        22100,  # 2022 World Archery Championships
        21000,  # 2021 Tokyo Olympics
    ]

    def get_competition_list(self) -> list[dict]:
        """Scrape the results calendar for all listed competitions."""
        soup = self.get(f"{BASE_URL}/events/results", wait_selector="a[href*='/competition/']", wait_ms=5000)
        if not soup:
            return []

        competitions = []
        for link in soup.select("a[href*='/competition/']"):
            href = link.get("href", "")
            match = re.search(r"/competition/(\d+)", href)
            if not match:
                continue
            comp_id = int(match.group(1))
            name = link.get_text(strip=True)
            if name and comp_id:
                competitions.append({
                    "id": comp_id,
                    "name": name,
                    "url": BASE_URL + href if href.startswith("/") else href,
                })

        # Deduplicate by id
        seen = set()
        unique = []
        for c in competitions:
            if c["id"] not in seen:
                seen.add(c["id"])
                unique.append(c)

        # Always include seeded IDs
        for comp_id in self.SEED_IDS:
            if comp_id not in seen:
                unique.append({
                    "id": comp_id,
                    "name": f"Competition {comp_id}",
                    "url": f"{BASE_URL}/competition/{comp_id}",
                })

        return unique

    def get_competition_detail(self, comp_id: int) -> dict:
        """Scrape metadata and results for a single competition."""
        url = f"{BASE_URL}/competition/{comp_id}"
        soup = self.get(url, wait_selector="h1", wait_ms=5000)
        if not soup:
            return {}

        detail = {"id": comp_id, "url": url, "events": []}

        # Title
        title_tag = soup.select_one("h1") or soup.select_one("h2")
        detail["name"] = title_tag.get_text(strip=True) if title_tag else f"Competition {comp_id}"

        # Dates and location from meta or visible text
        for tag in soup.select(".competition-date, .event-date, time"):
            detail.setdefault("date", tag.get_text(strip=True))
            break
        for tag in soup.select(".competition-location, .location, .venue"):
            detail.setdefault("location", tag.get_text(strip=True))
            break

        # Collect links to individual event result pages
        event_links = []
        for link in soup.select("a[href*='/results'], a[href*='/result']"):
            href = link.get("href", "")
            if str(comp_id) in href:
                event_links.append({
                    "name": link.get_text(strip=True),
                    "url": BASE_URL + href if href.startswith("/") else href,
                })

        detail["event_links"] = event_links

        # Try to parse embedded JSON data (Next.js / SSR apps often embed __NEXT_DATA__)
        next_data = self._extract_next_data(soup)
        if next_data:
            detail["raw_json"] = next_data

        return detail

    def get_event_results(self, event_url: str) -> list[dict]:
        """Scrape result rows from an individual event results page."""
        soup = self.get(event_url, wait_selector="table", wait_ms=6000)
        if not soup:
            return []

        results = []

        # Try standard result tables
        for table in soup.select("table"):
            headers = [th.get_text(strip=True).lower() for th in table.select("th")]
            for row in table.select("tr"):
                cells = [td.get_text(strip=True) for td in row.select("td")]
                if not cells:
                    continue
                row_dict = {}
                for i, val in enumerate(cells):
                    key = headers[i] if i < len(headers) else f"col_{i}"
                    row_dict[key] = val
                if row_dict:
                    results.append(row_dict)

        # Try embedded JSON
        if not results:
            next_data = self._extract_next_data(soup)
            if next_data:
                results = self._flatten_results_from_json(next_data)

        return results

    def get_medal_table(self, comp_id: int) -> list[dict]:
        """Scrape the medal table for a competition."""
        url = f"{BASE_URL}/competition/{comp_id}/medal-standings"
        soup = self.get(url, wait_selector="table", wait_ms=6000)
        if not soup:
            return []

        rows = []
        for table in soup.select("table"):
            headers = [th.get_text(strip=True).lower() for th in table.select("th")]
            for tr in table.select("tr"):
                cells = [td.get_text(strip=True) for td in tr.select("td")]
                if not cells:
                    continue
                row = {"competition_id": comp_id}
                for i, val in enumerate(cells):
                    key = headers[i] if i < len(headers) else f"col_{i}"
                    row[key] = val
                rows.append(row)
        return rows

    def _extract_next_data(self, soup) -> dict | None:
        """Extract JSON from Next.js __NEXT_DATA__ script tag if present."""
        tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if tag and tag.string:
            try:
                return json.loads(tag.string)
            except json.JSONDecodeError:
                pass
        return None

    def _flatten_results_from_json(self, data: dict) -> list[dict]:
        """Best-effort flatten of nested Next.js page props into result rows."""
        rows = []
        try:
            props = data.get("props", {}).get("pageProps", {})
            # Walk all lists in the props tree
            for val in props.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    rows.extend(val)
                    break
        except Exception:
            pass
        return rows
