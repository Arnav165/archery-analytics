"""
Archery Analytics — entry point.

Usage:
    python main.py fetch        # Download Olympic dataset → build SQLite DB
    python main.py dashboard    # Launch Streamlit dashboard
    python main.py all          # fetch + dashboard
"""
import subprocess
import sys


def run_fetch():
    import fetcher
    fetcher.run()


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
