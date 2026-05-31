from .base import BaseScraper, BASE_URL


class CountryScraper(BaseScraper):
    """Scrapes country/NOC medal standings from worldarchery.sport."""

    def get_country_list(self) -> list[dict]:
        """Scrape the list of member countries/NOCs."""
        url = f"{BASE_URL}/about-us/member-associations"
        soup = self.get(url)
        if not soup:
            return []

        countries = []
        for link in soup.select("a[href*='/member/'], a[href*='/country/']"):
            name = link.get_text(strip=True)
            href = link.get("href", "")
            if name:
                countries.append({
                    "name": name,
                    "url": BASE_URL + href if href.startswith("/") else href,
                })

        # Fallback: look for any list/grid of countries
        if not countries:
            for tag in soup.select("li, .country-item, .member-item"):
                text = tag.get_text(strip=True)
                if len(text) > 2:
                    countries.append({"name": text})

        return countries

    def get_all_time_medals(self) -> list[dict]:
        """
        Build an all-time medal table by aggregating medal tables
        from seeded competitions.
        """
        from .tournaments import TournamentScraper
        t = TournamentScraper(delay=self.delay)

        aggregated: dict[str, dict] = {}

        for comp_id in TournamentScraper.SEED_IDS:
            rows = t.get_medal_table(comp_id)
            for row in rows:
                country = row.get("country") or row.get("col_1") or row.get("noc", "")
                if not country:
                    continue
                if country not in aggregated:
                    aggregated[country] = {"country": country, "gold": 0, "silver": 0, "bronze": 0, "total": 0}
                for medal in ("gold", "silver", "bronze"):
                    try:
                        aggregated[country][medal] += int(row.get(medal, 0) or 0)
                    except ValueError:
                        pass
                aggregated[country]["total"] = (
                    aggregated[country]["gold"]
                    + aggregated[country]["silver"]
                    + aggregated[country]["bronze"]
                )

        return sorted(aggregated.values(), key=lambda x: x["total"], reverse=True)
