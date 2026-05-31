from .client import WAClient

# All ranked categories: R=Recurve, C=Compound, B=Barebow; M/W=Men/Women; X=Mixed Team
CATEGORIES = ["RM", "RW", "CM", "CW", "RX", "CX", "BM", "BW"]


class RankingsAPI:
    """Fetches world, continental, and World Cup rankings."""

    def __init__(self, client: WAClient):
        self.client = client

    def get_world_rankings(self, category: str | None = None) -> list[dict]:
        """
        Fetch world rankings. If category is given (e.g. 'RM'), fetch only
        that category. Otherwise fetch all CATEGORIES and return combined list.
        """
        if category:
            items = self.client.get_all("WorldRankings", {"Cat": category})
            for item in items:
                item["_category"] = category
            return items

        all_items = []
        for cat in CATEGORIES:
            items = self.client.get_all("WorldRankings", {"Cat": cat})
            for item in items:
                item["_category"] = cat
            print(f"  WorldRankings [{cat}]: {len(items)}")
            all_items.extend(items)
        return all_items

    def get_continental_rankings(self) -> list[dict]:
        """Fetch continental rankings across all categories."""
        all_items = []
        for cat in CATEGORIES:
            items = self.client.get_all("ContinentalRankings", {"Cat": cat})
            for item in items:
                item["_category"] = cat
            all_items.extend(items)
        print(f"  → {len(all_items)} continental ranking rows")
        return all_items

    def get_worldcup_rankings(self) -> list[dict]:
        """Fetch World Cup series rankings."""
        items = self.client.get_all("WorldCupRankings")
        print(f"  → {len(items)} World Cup ranking rows")
        return items
