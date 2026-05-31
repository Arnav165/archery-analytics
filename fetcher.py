"""
Downloads the Olympic history CSV, filters it to archery rows,
and stores everything in the SQLite database.
"""
import io
from pathlib import Path

import pandas as pd
import requests

CSV_URL = (
    "https://raw.githubusercontent.com/rgriff23/"
    "Olympic_history/master/data/athlete_events.csv"
)

RAW_DIR = Path(__file__).parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
DB_PATH = PROCESSED_DIR / "archery.db"

MEDAL_ORDER = {"Gold": 1, "Silver": 2, "Bronze": 3}


def _download_archery() -> pd.DataFrame:
    print("Downloading Olympic history dataset...")
    resp = requests.get(CSV_URL, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    archery = df[df["Sport"] == "Archery"].copy()
    print(f"  {len(archery):,} archery rows from {archery['Year'].min()}–{archery['Year'].max()}")
    return archery


def _build_events(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["Medal"] = df["Medal"].where(df["Medal"].isin(["Gold", "Silver", "Bronze"]), other=None)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["Height"] = pd.to_numeric(df["Height"], errors="coerce")
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    # Shorten event names: "Archery Men's Individual" → "Men's Individual"
    df["EventShort"] = df["Event"].str.replace("^Archery\\s*", "", regex=True).str.strip()
    return df.rename(columns=str.lower).reset_index(drop=True)


def _build_athletes(events: pd.DataFrame) -> pd.DataFrame:
    """One row per athlete: best stats + medal counts."""
    # Medal counts per athlete
    medals = (
        events[events["medal"].notna()]
        .groupby(["id", "medal"])
        .size()
        .unstack(fill_value=0)
        .rename(columns=str.lower)
        .reset_index()
    )
    for col in ("gold", "silver", "bronze"):
        if col not in medals.columns:
            medals[col] = 0
    medals["total_medals"] = medals["gold"] + medals["silver"] + medals["bronze"]

    # One row per athlete (most recent appearance)
    base = (
        events.sort_values("year", ascending=False)
        .drop_duplicates(subset=["id"])
        [["id", "name", "sex", "noc", "team", "age", "height", "weight"]]
    )

    # Years and events participated
    participation = events.groupby("id").agg(
        years_competed=("year", lambda x: sorted(x.unique().tolist())),
        games_count=("year", "nunique"),
        events_entered=("event", "count"),
        first_year=("year", "min"),
        last_year=("year", "max"),
    ).reset_index()

    df = base.merge(medals, on="id", how="left").merge(participation, on="id", how="left")
    for col in ("gold", "silver", "bronze", "total_medals"):
        df[col] = df[col].fillna(0).astype(int)
    return df.reset_index(drop=True)


def _build_competitions(events: pd.DataFrame) -> pd.DataFrame:
    """One row per Olympic Games, with archery event list."""
    grouped = events.groupby(["year", "city", "games"]).agg(
        event_count=("eventshort", "nunique"),
        athlete_count=("id", "nunique"),
        country_count=("noc", "nunique"),
        events=("eventshort", lambda x: sorted(x.unique().tolist())),
    ).reset_index()
    return grouped.sort_values("year", ascending=False).reset_index(drop=True)


def _build_medals(events: pd.DataFrame) -> pd.DataFrame:
    """Country-level medal table aggregated across all Olympic Games."""
    medal_rows = events[events["medal"].notna()].copy()
    agg = (
        medal_rows.groupby(["noc", "team", "medal"])
        .size()
        .unstack(fill_value=0)
        .rename(columns=str.lower)
        .reset_index()
    )
    for col in ("gold", "silver", "bronze"):
        if col not in agg.columns:
            agg[col] = 0
    agg["total"] = agg["gold"] + agg["silver"] + agg["bronze"]
    agg = agg.rename(columns={"team": "country"})
    return agg.sort_values("total", ascending=False).reset_index(drop=True)


def run():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    import sqlite3, json

    raw = _download_archery()
    raw.to_csv(RAW_DIR / "archery_raw.csv", index=False)
    print(f"[raw] Saved archery_raw.csv")

    events_df = _build_events(raw)
    athletes_df = _build_athletes(events_df)
    competitions_df = _build_competitions(events_df)
    medals_df = _build_medals(events_df)

    def save(df: pd.DataFrame, table: str):
        # Serialize list columns to JSON strings for SQLite
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda v: json.dumps(v) if isinstance(v, list) else v
                )
        with sqlite3.connect(DB_PATH) as conn:
            df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"[db] {len(df):,} rows → {table}")

    save(events_df, "events")
    save(athletes_df, "athletes")
    save(competitions_df, "competitions")
    save(medals_df, "medals")

    print(f"\n✓ Done. DB at {DB_PATH}")
