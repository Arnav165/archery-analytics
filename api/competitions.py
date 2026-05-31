from .client import WAClient


class CompetitionsAPI:
    """Fetches competition metadata, medallists, and medal tables."""

    def __init__(self, client: WAClient):
        self.client = client

    def get_competitions(self, with_results_only: bool = True) -> list[dict]:
        """All competitions. Pass with_results_only=True to skip future events."""
        params = {}
        if with_results_only:
            params["WithRes"] = 1
        items = self.client.get_all("Competitions", params)
        print(f"  → {len(items)} competitions")
        return items

    def get_medallists(self, competition_id: int | str) -> list[dict]:
        """
        Medal results for a single competition.
        Returns a flat list: one row per athlete-medal combination.
        """
        data = self.client.get("CompetitionMedallists", {"ID": competition_id})
        items = data.get("items", [])

        flat = []
        for category in items:
            cat_code = category.get("Code", "")
            is_team = category.get("IsTeam", False)
            for result in category.get("Results", []):
                medal = result.get("Medal", "")
                noc = result.get("NOC", "")
                country_name = result.get("Name", "")
                for athlete in result.get("Athletes", []):
                    flat.append({
                        "competition_id": competition_id,
                        "category": cat_code,
                        "is_team": is_team,
                        "medal": medal,
                        "noc": noc,
                        "country_name": country_name,
                        "athlete_id": athlete.get("Id"),
                        "athlete_fname": athlete.get("FName", ""),
                        "athlete_gname": athlete.get("GName", ""),
                    })
        return flat

    def get_medals_table(self, competition_id: int | str) -> list[dict]:
        """Country-level medal table for one competition."""
        data = self.client.get("MedalsTable", {"ID": competition_id})
        items = data.get("items", [])
        for item in items:
            item["competition_id"] = competition_id
        return items

    def get_all_medallists(self, competition_ids: list[int | str]) -> list[dict]:
        """Fetch and flatten medallists for a list of competition IDs."""
        all_rows = []
        for i, cid in enumerate(competition_ids, 1):
            rows = self.get_medallists(cid)
            all_rows.extend(rows)
            if i % 10 == 0:
                print(f"  Medallists: {i}/{len(competition_ids)} competitions done")
        print(f"  → {len(all_rows)} medallist rows total")
        return all_rows
