from .client import WAClient


class AthletesAPI:
    """Fetches athlete lists and full biographies."""

    def __init__(self, client: WAClient):
        self.client = client

    def get_athletes(self) -> list[dict]:
        """All athletes (Id, FName, GName, NOC)."""
        print("  Fetching athlete list...")
        items = self.client.get_all("Athletes")
        print(f"  → {len(items)} athletes")
        return items

    def get_biography(self, athlete_id: int | str) -> dict | None:
        """Full biography for one athlete including stats, medals, rankings."""
        data = self.client.get("AthleteBiography", {"Id": athlete_id})
        items = data.get("items", [])
        return items[0] if items else None

    def get_biographies(self, athlete_ids: list[int | str]) -> list[dict]:
        """Fetch biographies for a list of athlete IDs."""
        bios = []
        total = len(athlete_ids)
        for i, aid in enumerate(athlete_ids, 1):
            bio = self.get_biography(aid)
            if bio:
                bios.append(bio)
            if i % 50 == 0:
                print(f"  Biographies: {i}/{total}")
        print(f"  → {len(bios)} biographies fetched")
        return bios
