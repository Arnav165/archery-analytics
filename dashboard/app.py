import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.components import world_map, head_to_head, tournament_browser

DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "archery.db"

st.set_page_config(
    page_title="Archery Analytics",
    page_icon="🏹",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    body, .stApp { background-color: #0e1117; color: #fafafa; }
    .stMetric { background: #1a1a2e; border-radius: 8px; padding: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_data() -> dict[str, pd.DataFrame]:
    if not DB_PATH.exists():
        # Auto-fetch on first deploy (no DB committed to repo)
        with st.spinner("Building database from Olympic dataset — takes ~10 seconds..."):
            import fetcher
            fetcher.run()
    if not DB_PATH.exists():
        return {k: pd.DataFrame() for k in ("events", "athletes", "competitions", "medals")}
    with sqlite3.connect(DB_PATH) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        return {t: pd.read_sql(f"SELECT * FROM {t}", conn) for t in tables}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏹 Archery Analytics")
    st.caption("Olympic Archery · 1900–2016")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["World Medal Map", "Head-to-Head", "Tournament Browser"],
        key="nav",
    )
    st.markdown("---")
    if st.button("🔄 Refresh cache"):
        st.cache_data.clear()
        st.rerun()

# ── Load ──────────────────────────────────────────────────────────────────────
data = load_data()

if data.get("medals", pd.DataFrame()).empty:
    st.sidebar.warning("No data yet — run: `python main.py fetch`")
else:
    total = int(data["medals"]["total"].sum()) if "total" in data["medals"].columns else 0
    st.sidebar.success(f"{total} medals across {len(data.get('competitions', []))} Games")

# ── Pages ─────────────────────────────────────────────────────────────────────
if page == "World Medal Map":
    world_map.render(data.get("medals", pd.DataFrame()))

elif page == "Head-to-Head":
    head_to_head.render(
        data.get("events", pd.DataFrame()),
        data.get("athletes", pd.DataFrame()),
    )

elif page == "Tournament Browser":
    tournament_browser.render(
        data.get("competitions", pd.DataFrame()),
        data.get("events", pd.DataFrame()),
    )
