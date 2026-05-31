import json

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st


def _parse_years(val) -> list[int]:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            pass
    return []


def _stats(athletes_df: pd.DataFrame, name: str) -> dict:
    row = athletes_df[athletes_df["name"] == name]
    if row.empty:
        return {}
    r = row.iloc[0].to_dict()
    r["years"] = _parse_years(r.get("years_competed", []))
    return r


def _medal_bar(a: dict, b: dict) -> go.Figure:
    fig = go.Figure()
    for stats, color in [(a, "#e94560"), (b, "#f5c518")]:
        fig.add_trace(go.Bar(
            name=stats["name"],
            x=["Gold", "Silver", "Bronze", "Games"],
            y=[stats.get("gold", 0), stats.get("silver", 0),
               stats.get("bronze", 0), stats.get("games_count", 0)],
            marker_color=color,
        ))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="#0e1117", plot_bgcolor="#1a1a2e",
        font_color="#fafafa", height=320,
        margin=dict(t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def _timeline(events_df: pd.DataFrame, name_a: str, name_b: str) -> go.Figure:
    sub = events_df[events_df["name"].isin([name_a, name_b])].copy()
    sub = sub[sub["medal"].notna()]
    if sub.empty:
        return None

    medal_sym = {"Gold": "star", "Silver": "circle", "Bronze": "diamond"}
    name_color = {name_a: "#e94560", name_b: "#f5c518"}

    fig = px.scatter(
        sub, x="year", y="name",
        color="name",
        symbol="medal",
        symbol_map=medal_sym,
        color_discrete_map=name_color,
        hover_data={"eventshort": True, "city": True, "medal": True, "year": True, "name": False},
        title="Medal Timeline",
    )
    fig.update_traces(marker_size=14)
    fig.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#1a1a2e",
        font_color="#fafafa", height=280,
        margin=dict(t=40, b=10),
        showlegend=False,
        xaxis=dict(dtick=4),
    )
    return fig


def render(events_df: pd.DataFrame, athletes_df: pd.DataFrame):
    st.subheader("Head-to-Head Athlete Comparison")

    if athletes_df.empty:
        st.info("No data yet — run `python main.py fetch` first.")
        return

    # Only show athletes who won at least one medal to keep the list useful
    medalists = athletes_df[athletes_df["total_medals"] > 0].sort_values(
        "total_medals", ascending=False
    )
    names = medalists["name"].tolist()

    if len(names) < 2:
        st.info("Not enough medal data to compare athletes.")
        return

    col1, col2 = st.columns(2)
    with col1:
        name_a = st.selectbox("Athlete A", names, index=0, key="h2h_a")
    with col2:
        name_b = st.selectbox("Athlete B", names, index=min(1, len(names) - 1), key="h2h_b")

    if name_a == name_b:
        st.warning("Select two different athletes.")
        return

    a = _stats(athletes_df, name_a)
    b = _stats(athletes_df, name_b)

    # ── Stat cards ────────────────────────────────────────────────────
    ca, cb = st.columns(2)
    for col, s in [(ca, a), (cb, b)]:
        with col:
            st.markdown(f"#### {s['name']}")
            m1, m2, m3, m4 = col.columns(4)
            m1.metric("🥇 Gold", s.get("gold", 0))
            m2.metric("🥈 Silver", s.get("silver", 0))
            m3.metric("🥉 Bronze", s.get("bronze", 0))
            m4.metric("Games", s.get("games_count", 0))
            st.caption(
                f"**{s.get('noc','')}** · "
                f"{'M' if s.get('sex') == 'M' else 'F'} · "
                f"Years: {', '.join(str(y) for y in s.get('years', []))}"
            )

    # ── Charts ────────────────────────────────────────────────────────
    st.plotly_chart(_medal_bar(a, b), use_container_width=True)

    if not events_df.empty:
        fig = _timeline(events_df, name_a, name_b)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    # ── Event history tables ──────────────────────────────────────────
    if not events_df.empty:
        st.markdown("---")
        ta, tb = st.columns(2)
        for col, name in [(ta, name_a), (tb, name_b)]:
            with col:
                st.markdown(f"**{name} — event history**")
                rows = events_df[events_df["name"] == name][
                    ["year", "city", "eventshort", "medal"]
                ].sort_values("year", ascending=False)
                st.dataframe(rows.reset_index(drop=True), use_container_width=True)
