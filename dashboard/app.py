import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import DataPipeline
from dashboard.components import world_map, head_to_head, tournament_browser

st.set_page_config(
    page_title="Archery Analytics",
    page_icon="🏹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme overrides
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
def load_data():
    pipeline = DataPipeline()
    return {
        "competitions": pipeline.load("competitions"),
        "athletes": pipeline.load("biographies"),
        "medals": pipeline.load("medals"),
        "medallists": pipeline.load("medallists"),
        "rankings": pipeline.load("rankings"),
        "records": pipeline.load("records"),
    }


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏹 Archery Analytics")
    st.markdown("Data sourced from [World Archery API](https://api.worldarchery.org/v4/API/)")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["World Medal Map", "Head-to-Head", "Tournament Browser"],
        key="nav",
    )
    st.markdown("---")
    if st.button("🔄 Refresh data cache"):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
data = load_data()

tables_loaded = [k for k, v in data.items() if not v.empty]
if tables_loaded:
    st.sidebar.success(f"Loaded: {', '.join(tables_loaded)}")
else:
    st.sidebar.warning("No data found. Run: `python main.py fetch`")

# ── Pages ─────────────────────────────────────────────────────────────────────
if page == "World Medal Map":
    world_map.render(data["medals"])

elif page == "Head-to-Head":
    head_to_head.render(data["medallists"], data["athletes"])

elif page == "Tournament Browser":
    tournament_browser.render(data["competitions"], data["medallists"])
