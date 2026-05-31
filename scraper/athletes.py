import re
from .base import BaseScraper, BASE_URL


class AthleteScraper(BaseScraper):
    """Scrapes athlete profiles and world rankings from worldarchery.sport."""

    DISCIPLINES = ["recurve", "compound", "barebow"]
    GENDERS = ["men", "women", "mixed-team"]

    def get_rankings(self, discipline: str = "recurve", gender: str = "men") -> list[dict]:
        """Scrape world rankings for a given discipline and gender."""
        url = f"{BASE_URL}/rankings/world-ranking?discipline={discipline}&gender={gender}"
        soup = self.get(url)
        if not soup:
            return []

        athletes = []
        for table in soup.select("table"):
            headers = [th.get_text(strip=True).lower() for th in table.select("th")]
            for tr in table.select("tr"):
                cells = [td.get_text(strip=True) for td in tr.select("td")]
                if not cells:
                    continue
                row = {"discipline": discipline, "gender": gender}
                for i, val in enumerate(cells):
                    key = headers[i] if i < len(headers) else f"col_{i}"
                    row[key] = val

                # Extract athlete profile link if present
                # Profile links may appear as /athletes/{id} or /athlete/{id}
                for a in tr.select("a[href*='/athlete']"):
                    href = a.get("href", "")
                    match = re.search(r"/athletes?/(\d+)", href)
                    if match:
                        row["athlete_id"] = int(match.group(1))
                        row["profile_url"] = BASE_URL + href if href.startswith("/") else href
                        break

                athletes.append(row)

        return athletes

    def get_all_rankings(self) -> list[dict]:
        """Scrape rankings for all disciplines and genders."""
        all_rows = []
        for discipline in self.DISCIPLINES:
            for gender in self.GENDERS:
                rows = self.get_rankings(discipline, gender)
                all_rows.extend(rows)
                print(f"  Rankings [{discipline}/{gender}]: {len(rows)} athletes")
        return all_rows

    def get_athlete_profile(self, athlete_id: int) -> dict:
        """Scrape an individual athlete's profile page."""
        url = f"{BASE_URL}/athletes/{athlete_id}"
        soup = self.get(url)
        if not soup:
            return {}

        profile = {"athlete_id": athlete_id, "url": url}

        # Name
        name_tag = soup.select_one("h1") or soup.select_one(".athlete-name")
        if name_tag:
            profile["name"] = name_tag.get_text(strip=True)

        # Country
        country_tag = soup.select_one(".athlete-country, .country-name, [class*='country']")
        if country_tag:
            profile["country"] = country_tag.get_text(strip=True)

        # Country flag/code from img alt or class
        flag = soup.select_one("img[class*='flag'], .flag img")
        if flag:
            profile["country_code"] = flag.get("alt", "").strip()

        # Stats table (DOB, discipline, etc.)
        for row in soup.select("table tr, .profile-detail, dl"):
            label = row.select_one("th, dt, .label")
            value = row.select_one("td, dd, .value")
            if label and value:
                key = label.get_text(strip=True).lower().replace(" ", "_")
                profile[key] = value.get_text(strip=True)

        # Results summary
        results = []
        for table in soup.select("table"):
            headers = [th.get_text(strip=True).lower() for th in table.select("th")]
            if not any(h in headers for h in ["competition", "event", "result", "medal"]):
                continue
            for tr in table.select("tr"):
                cells = [td.get_text(strip=True) for td in tr.select("td")]
                if cells:
                    row_dict = {"athlete_id": athlete_id}
                    for i, val in enumerate(cells):
                        key = headers[i] if i < len(headers) else f"col_{i}"
                        row_dict[key] = val
                    results.append(row_dict)

        profile["results"] = results
        return profile
