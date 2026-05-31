"""
Entry point for the archery analytics project.

Usage:
    python main.py scrape       # Phase 1 + 2: scrape then clean & store
    python main.py dashboard    # Phase 3: launch Streamlit dashboard
    python main.py all          # scrape + launch dashboard
"""
import subprocess
import sys

from pipeline import DataPipeline
from scraper import TournamentScraper, AthleteScraper, CountryScraper


def run_scrape():
    pipeline = DataPipeline()
    t_scraper = TournamentScraper()
    a_scraper = AthleteScraper()
    c_scraper = CountryScraper()

    # --- Tournaments ---
    print("\n[1/4] Scraping competition list...")
    competitions = t_scraper.get_competition_list()
    pipeline.save_raw(competitions, "competitions_raw")
    tournaments_df = pipeline.clean_tournaments(competitions)
    pipeline.to_sqlite(tournaments_df, "tournaments")
    print(f"      {len(tournaments_df)} tournaments stored.")

    # --- Results (seed IDs only to avoid hammering the server) ---
    print("\n[2/4] Scraping event results for seeded competitions...")
    all_results = []
    for comp in competitions[:10]:  # limit to first 10 on initial run
        comp_id = comp["id"]
        detail = t_scraper.get_competition_detail(comp_id)
        for event in detail.get("event_links", [])[:5]:  # max 5 events per comp
            rows = t_scraper.get_event_results(event["url"])
            for r in rows:
                r["competition_id"] = comp_id
                r["competition_name"] = comp.get("name", "")
            all_results.extend(rows)
        print(f"      comp {comp_id}: {len(detail.get('event_links', []))} events found")

    pipeline.save_raw(all_results, "results_raw")
    results_df = pipeline.clean_results(all_results)
    pipeline.to_sqlite(results_df, "results")
    print(f"      {len(results_df)} result rows stored.")

    # --- Athletes / Rankings ---
    print("\n[3/4] Scraping world rankings...")
    rankings = a_scraper.get_all_rankings()
    pipeline.save_raw(rankings, "rankings_raw")
    athletes_df = pipeline.clean_athletes(rankings)
    pipeline.to_sqlite(athletes_df, "athletes")
    print(f"      {len(athletes_df)} athlete records stored.")

    # --- Country medal table ---
    print("\n[4/4] Building all-time medal table...")
    medals = c_scraper.get_all_time_medals()
    pipeline.save_raw(medals, "medals_raw")
    medals_df = pipeline.clean_medals(medals)
    pipeline.to_sqlite(medals_df, "medals")
    print(f"      {len(medals_df)} countries in medal table.")

    print("\n✓ Scrape complete. Data stored in data/processed/archery.db")


def run_dashboard():
    print("Launching Streamlit dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/app.py"], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "scrape":
        run_scrape()
    elif cmd == "dashboard":
        run_dashboard()
    elif cmd == "all":
        run_scrape()
        run_dashboard()
    else:
        print(__doc__)
