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
    # Save raw scraped data as JSON
    # ------------------------------------------------------------------

    def save_raw(self, data: list | dict, name: str) -> Path:
        path = RAW_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[raw] Saved {len(data) if isinstance(data, list) else 1} records → {path}")
        return path

    # ------------------------------------------------------------------
    # Clean individual datasets
    # ------------------------------------------------------------------

    def clean_tournaments(self, raw: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df = df.drop_duplicates(subset=["id"]) if "id" in df.columns else df
        for col in ("name", "location"):
            if col in df.columns:
                df[col] = df[col].str.strip().str.title()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.reset_index(drop=True)

    def clean_athletes(self, raw: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        for col in ("name", "country", "discipline", "gender"):
            if col in df.columns:
                df[col] = df[col].str.strip()
        if "name" in df.columns:
            df["name"] = df["name"].str.title()
        # Normalize rank column
        for rank_col in ("rank", "ranking", "position", "col_0"):
            if rank_col in df.columns:
                df["rank"] = pd.to_numeric(df[rank_col], errors="coerce")
                break
        return df.drop_duplicates().reset_index(drop=True)

    def clean_medals(self, raw: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        for col in ("gold", "silver", "bronze", "total"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        if "country" in df.columns:
            df["country"] = df["country"].str.strip().str.upper()
        return df.sort_values("total", ascending=False).reset_index(drop=True)

    def clean_results(self, raw: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df = df.dropna(how="all")
        # Normalise common column name variants
        rename_map = {
            "pos": "position", "place": "position", "rank": "position",
            "athlete": "name", "archer": "name",
            "noc": "country_code", "nat": "country_code",
            "pts": "points", "score": "points",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if "points" in df.columns:
            df["points"] = pd.to_numeric(df["points"], errors="coerce")
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Persist to SQLite
    # ------------------------------------------------------------------

    def to_sqlite(self, df: pd.DataFrame, table: str, if_exists: str = "replace"):
        if df.empty:
            print(f"[pipeline] Skipping empty dataframe for table '{table}'")
            return
        # Serialize list/dict columns to JSON strings
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v
                )
        with sqlite3.connect(DB_PATH) as conn:
            df.to_sql(table, conn, if_exists=if_exists, index=False)
        print(f"[db] {len(df)} rows → {table} ({DB_PATH.name})")

    # ------------------------------------------------------------------
    # Load from SQLite
    # ------------------------------------------------------------------

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
