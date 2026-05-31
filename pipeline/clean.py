import json
import sqlite3
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
DB_PATH = PROCESSED_DIR / "archery.db"


class DataPipeline:
    def __init__(self):
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Save raw API JSON responses
    # ------------------------------------------------------------------

    def save_raw(self, data: list | dict, name: str) -> Path:
        path = RAW_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        count = len(data) if isinstance(data, list) else 1
        print(f"[raw] {count} records → {path.name}")
        return path

    # ------------------------------------------------------------------
    # Clean: Athletes
    # ------------------------------------------------------------------

    def clean_athletes(self, raw: list[dict]) -> pd.DataFrame:
        """Flatten the Athletes list endpoint (Id, FName, GName, NOC)."""
        rows = []
        for item in raw:
            rows.append({
                "athlete_id": item.get("Id"),
                "last_name": item.get("FName", ""),
                "first_name": item.get("GName", ""),
                "noc": item.get("NOC", ""),
                "name": f"{item.get('GName', '')} {item.get('FName', '')}".strip(),
            })
        df = pd.DataFrame(rows).drop_duplicates(subset=["athlete_id"])
        return df.reset_index(drop=True)

    def clean_biographies(self, raw: list[dict]) -> pd.DataFrame:
        """Flatten AthleteBiography items into one row per athlete."""
        rows = []
        for item in raw:
            wr = item.get("WorldRankings", {})
            current_rankings = wr.get("Current", [{}])
            best_rankings = wr.get("Best", [{}])
            wr_current = current_rankings[0] if current_rankings else {}
            wr_best = best_rankings[0] if best_rankings else {}

            stats = item.get("Stats", {})
            career = stats.get("Career", {})

            rows.append({
                "athlete_id": item.get("Id"),
                "last_name": item.get("FName", ""),
                "first_name": item.get("GName", ""),
                "noc": item.get("NOC", ""),
                "country": item.get("CountryName", ""),
                "gender": item.get("Gender", ""),
                "dob": item.get("DoB", ""),
                "age": item.get("Age"),
                "continental_assoc": item.get("ContinentalAssoc", ""),
                "wr_current_rank": wr_current.get("Rnk"),
                "wr_current_points": wr_current.get("Points"),
                "wr_current_category": wr_current.get("CatCode", ""),
                "wr_best_rank": wr_best.get("Rnk"),
                "wr_best_category": wr_best.get("CatCode", ""),
                "career_events": career.get("Events"),
                "career_match_win_pct": career.get("MatchWinPercentage"),
                "career_qual_best": career.get("QBest"),
                "medal_count": len(item.get("Medals", [])),
            })
        df = pd.DataFrame(rows).drop_duplicates(subset=["athlete_id"])
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Clean: Rankings
    # ------------------------------------------------------------------

    def clean_rankings(self, raw: list[dict]) -> pd.DataFrame:
        """Flatten WorldRankings items (Rnk, Cat, Points, Athlete nested obj)."""
        rows = []
        for item in raw:
            athlete = item.get("Athlete", {})
            rows.append({
                "rank": item.get("Rnk"),
                "rank_prev": item.get("RnkOld"),
                "category": item.get("Cat") or item.get("_category", ""),
                "points": item.get("Points"),
                "date_issued": item.get("RnkDtIssued", ""),
                "date_since": item.get("RnkDtSince", ""),
                "athlete_id": athlete.get("Id"),
                "last_name": athlete.get("FName", ""),
                "first_name": athlete.get("GName", ""),
                "noc": athlete.get("NOC", ""),
            })
        df = pd.DataFrame(rows)
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
        df["points"] = pd.to_numeric(df["points"], errors="coerce")
        return df.sort_values(["category", "rank"]).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Clean: Competitions
    # ------------------------------------------------------------------

    def clean_competitions(self, raw: list[dict]) -> pd.DataFrame:
        rows = []
        for item in raw:
            rows.append({
                "competition_id": item.get("ID"),
                "name": item.get("Name", ""),
                "name_short": item.get("NameShort", ""),
                "venue": item.get("Venue", ""),
                "place": item.get("Place", ""),
                "country": item.get("Country", ""),
                "country_name": item.get("CountryName", ""),
                "date_from": item.get("DFrom", ""),
                "date_to": item.get("DTo", ""),
                "level": item.get("Level", ""),
                "event_type": item.get("EventType", ""),
                "is_world_ranking_event": item.get("WorldRankingEvent", False),
                "with_results": item.get("WithRes", False),
                "is_cancelled": item.get("IsCancelled", False),
            })
        df = pd.DataFrame(rows).drop_duplicates(subset=["competition_id"])
        df["date_from"] = pd.to_datetime(df["date_from"], errors="coerce")
        df["date_to"] = pd.to_datetime(df["date_to"], errors="coerce")
        return df.sort_values("date_from", ascending=False).reset_index(drop=True)

    def clean_medallists(self, raw: list[dict]) -> pd.DataFrame:
        """Already flat from CompetitionsAPI.get_medallists — just type-cast."""
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df["athlete_id"] = pd.to_numeric(df["athlete_id"], errors="coerce")
        df["medal"] = df["medal"].str.strip().str.title()
        return df.drop_duplicates().reset_index(drop=True)

    def clean_medals_table(self, raw: list[dict]) -> pd.DataFrame:
        """Aggregate country medal counts across all competitions."""
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        for col in ("Gold", "Silver", "Bronze", "Total"):
            if col in df.columns:
                df[col.lower()] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        noc_col = next((c for c in df.columns if c.lower() in ("noc", "country", "countrycode")), None)
        if noc_col:
            df = df.rename(columns={noc_col: "noc"})
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Clean: Records
    # ------------------------------------------------------------------

    def clean_records(self, raw: list[dict]) -> pd.DataFrame:
        """Already flat from RecordsAPI._flatten."""
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df["points"] = pd.to_numeric(df["points"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.drop_duplicates().reset_index(drop=True)

    # ------------------------------------------------------------------
    # SQLite persistence
    # ------------------------------------------------------------------

    def to_sqlite(self, df: pd.DataFrame, table: str, if_exists: str = "replace"):
        if df.empty:
            print(f"[db] Skipping empty table '{table}'")
            return
        # Serialize any remaining list/dict columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v
                )
        with sqlite3.connect(DB_PATH) as conn:
            df.to_sql(table, conn, if_exists=if_exists, index=False)
        print(f"[db] {len(df):,} rows → {table}")

    def load(self, table: str) -> pd.DataFrame:
        if not DB_PATH.exists():
            return pd.DataFrame()
        with sqlite3.connect(DB_PATH) as conn:
            try:
                return pd.read_sql(f"SELECT * FROM {table}", conn)
            except Exception:
                return pd.DataFrame()

    def list_tables(self) -> list[str]:
        if not DB_PATH.exists():
            return []
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [r[0] for r in cur.fetchall()]
