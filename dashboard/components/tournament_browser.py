import json

import pandas as pd
import plotly.express as px
import streamlit as st


def _parse_events(val) -> list[str]:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            pass
    return []


def render(competitions_df: pd.DataFrame, events_df: pd.DataFrame):
    st.subheader("Tournament Browser")
    st.caption("Every Olympic Games that included archery · 1900–2016")

    if competitions_df.empty:
        st.info("No data yet — run `python main.py fetch` first.")
        return

    # ── Filters ───────────────────────────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        years = sorted(competitions_df["year"].dropna().astype(int).unique(), reverse=True)
        selected_year = st.selectbox("Year", ["All"] + [str(y) for y in years], key="tb_year")
    with fc2:
        search = st.text_input("Search city or Games name", key="tb_search")

    df = competitions_df.copy()
    if selected_year != "All":
        df = df[df["year"] == int(selected_year)]
    if search:
        mask = (
            df["city"].str.contains(search, case=False, na=False)
            | df["games"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    st.markdown(f"**{len(df)} Games found**")
    if df.empty:
        st.warning("No Games match the selected filters.")
        return

    # ── Games list ────────────────────────────────────────────────────
    display = df[["year", "city", "athlete_count", "country_count", "event_count"]].rename(
        columns={
            "year": "Year", "city": "City",
            "athlete_count": "Athletes", "country_count": "Countries",
            "event_count": "Events",
        }
    )
    st.dataframe(display.reset_index(drop=True), use_container_width=True)

    # ── Drill into one Games ──────────────────────────────────────────
    game_options = df["games"].tolist()
    selected_game = st.selectbox("Explore a Games", game_options, key="tb_game")
    game_row = df[df["games"] == selected_game].iloc[0]

    yr = int(game_row["year"])
    city = game_row["city"]
    st.markdown(f"### {selected_game} — Archery")

    m1, m2, m3 = st.columns(3)
    m1.metric("Athletes", int(game_row["athlete_count"]))
    m2.metric("Countries", int(game_row["country_count"]))
    m3.metric("Events", int(game_row["event_count"]))

    event_list = _parse_events(game_row.get("events", []))
    if event_list:
        st.markdown("**Disciplines:** " + " · ".join(event_list))

    if events_df.empty:
        return

    game_events = events_df[events_df["year"] == yr].copy()
    if game_events.empty:
        st.info("No event-level data for this Games.")
        return

    # ── Medallists ────────────────────────────────────────────────────
    medal_rows = game_events[game_events["medal"].notna()].sort_values(
        ["eventshort", "medal"]
    )[["eventshort", "medal", "name", "noc"]].rename(
        columns={"eventshort": "Event", "medal": "Medal", "name": "Athlete", "noc": "NOC"}
    )

    if not medal_rows.empty:
        st.markdown("#### Medallists")
        st.dataframe(medal_rows.reset_index(drop=True), use_container_width=True)

    # ── Country breakdown ─────────────────────────────────────────────
    country_medals = (
        game_events[game_events["medal"].notna()]
        .groupby(["noc", "medal"])
        .size()
        .unstack(fill_value=0)
        .rename(columns=str.lower)
        .reset_index()
    )
    for col in ("gold", "silver", "bronze"):
        if col not in country_medals.columns:
            country_medals[col] = 0
    country_medals["total"] = country_medals["gold"] + country_medals["silver"] + country_medals["bronze"]
    country_medals = country_medals.sort_values("total", ascending=False)

    if not country_medals.empty:
        fig = px.bar(
            country_medals.head(15),
            x="noc", y=["gold", "silver", "bronze"],
            title=f"Medal Table — {city} {yr}",
            color_discrete_map={"gold": "#f5c518", "silver": "#c0c0c0", "bronze": "#cd7f32"},
            barmode="stack",
        )
        fig.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1a2e",
            font_color="#fafafa", height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=10),
            xaxis_title="Country (NOC)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Participation by country ───────────────────────────────────────
    participation = (
        game_events.groupby("noc")["id"]
        .nunique()
        .reset_index()
        .rename(columns={"id": "athletes", "noc": "NOC"})
        .sort_values("athletes", ascending=False)
    )
    with st.expander("All participating countries"):
        st.dataframe(participation.reset_index(drop=True), use_container_width=True)
