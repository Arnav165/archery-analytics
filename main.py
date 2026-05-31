"""
Archery Analytics — entry point.

Usage:
    python main.py fetch        # Pull data from World Archery API → store in SQLite
    python main.py dashboard    # Launch Streamlit dashboard
    python main.py all          # fetch + dashboard
"""
import subprocess
import sys

from api import AthletesAPI, RankingsAPI, CompetitionsAPI, RecordsAPI
from api.client import WAClient
from pipeline import DataPipeline


def run_fetch():
    client = WAClient(delay=0.3)
    pipeline = DataPipeline()

    athletes_api = AthletesAPI(client)
    rankings_api = RankingsAPI(client)
    comps_api = CompetitionsAPI(client)
    records_api = RecordsAPI(client)

    # ── Athletes ──────────────────────────────────────────────────────
    print("\n[1/4] Athletes")
    athletes_raw = athletes_api.get_athletes()
    pipeline.save_raw(athletes_raw, "athletes_raw")
    athletes_df = pipeline.clean_athletes(athletes_raw)
    pipeline.to_sqlite(athletes_df, "athletes")

    # Fetch full biographies for the first 200 athletes to keep runtime
    # reasonable on first run. Remove the slice to get everyone.
    athlete_ids = [a["athlete_id"] for a in athletes_raw[:200] if a.get("athlete_id")]
    bios_raw = athletes_api.get_biographies(athlete_ids)
    pipeline.save_raw(bios_raw, "biographies_raw")
    bios_df = pipeline.clean_biographies(bios_raw)
    pipeline.to_sqlite(bios_df, "biographies")

    # ── Rankings ──────────────────────────────────────────────────────
    print("\n[2/4] World Rankings")
    rankings_raw = rankings_api.get_world_rankings()
    pipeline.save_raw(rankings_raw, "rankings_raw")
    rankings_df = pipeline.clean_rankings(rankings_raw)
    pipeline.to_sqlite(rankings_df, "rankings")

    # ── Competitions + Medallists ─────────────────────────────────────
    print("\n[3/4] Competitions & Medallists")
    comps_raw = comps_api.get_competitions(with_results_only=True)
    pipeline.save_raw(comps_raw, "competitions_raw")
    comps_df = pipeline.clean_competitions(comps_raw)
    pipeline.to_sqlite(comps_df, "competitions")

    # Fetch medallists for the 50 most recent competitions
    recent_ids = comps_df["competition_id"].dropna().astype(int).tolist()[:50]
    medallists_raw = comps_api.get_all_medallists(recent_ids)
    pipeline.save_raw(medallists_raw, "medallists_raw")
    medallists_df = pipeline.clean_medallists(medallists_raw)
    pipeline.to_sqlite(medallists_df, "medallists")

    # Build country medal aggregate from medallists
    if not medallists_df.empty:
        medals_agg = (
            medallists_df.groupby(["noc", "medal"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        for col in ("Gold", "Silver", "Bronze"):
            if col not in medals_agg.columns:
                medals_agg[col] = 0
        medals_agg["total"] = medals_agg.get("Gold", 0) + medals_agg.get("Silver", 0) + medals_agg.get("Bronze", 0)
        medals_agg = medals_agg.rename(columns={"noc": "country", "Gold": "gold", "Silver": "silver", "Bronze": "bronze"})
        pipeline.to_sqlite(medals_agg, "medals")

    # ── Records ───────────────────────────────────────────────────────
    print("\n[4/4] World Records")
    records_raw = records_api.get_records()
    pipeline.save_raw(records_raw, "records_raw")
    records_df = pipeline.clean_records(records_raw)
    pipeline.to_sqlite(records_df, "records")

    print(f"\n✓ Done. Tables: {pipeline.list_tables()}")


def run_dashboard():
    print("Launching Streamlit dashboard...")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"],
        check=True,
    )


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "fetch":
        run_fetch()
    elif cmd == "dashboard":
        run_dashboard()
    elif cmd == "all":
        run_fetch()
        run_dashboard()
    else:
        print(__doc__)
