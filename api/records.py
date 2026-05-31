from .client import WAClient


class RecordsAPI:
    """Fetches world records and record history."""

    def __init__(self, client: WAClient):
        self.client = client

    def get_records(self) -> list[dict]:
        """All current standing world records."""
        items = self.client.get_all("Records")
        print(f"  → {len(items)} records")
        return self._flatten(items)

    def get_record_history(self) -> list[dict]:
        """Full history of all records (including broken ones)."""
        items = self.client.get_all("RecordHistory")
        print(f"  → {len(items)} record history rows")
        return self._flatten(items)

    def _flatten(self, items: list[dict]) -> list[dict]:
        """Flatten nested Archers and Competition objects into simple rows."""
        flat = []
        for record in items:
            competition = record.get("Competition") or {}
            archers = record.get("Archers") or []
            if not archers:
                archers = [{}]
            for archer in archers:
                flat.append({
                    "record_name": record.get("RecordName", ""),
                    "record_sub_name": record.get("RecordSubName", ""),
                    "category": record.get("Cat", ""),
                    "is_team": record.get("IsTeam", False),
                    "points": record.get("Points"),
                    "xs": record.get("Xs"),
                    "max_points": record.get("MaxPoints"),
                    "date": record.get("Date", ""),
                    "noc": record.get("NOC", ""),
                    "record_standing": record.get("RecordStanding", False),
                    "para": record.get("ParaAr", False),
                    "competition_id": competition.get("ID"),
                    "competition_name": competition.get("Name", ""),
                    "competition_place": competition.get("Place", ""),
                    "athlete_id": archer.get("Id"),
                    "athlete_fname": archer.get("FName", ""),
                    "athlete_gname": archer.get("GName", ""),
                    "athlete_noc": archer.get("NOC", archer.get("noc", "")),
                })
        return flat
