import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _get_athlete_stats(results_df: pd.DataFrame, athletes_df: pd.DataFrame, name: str) -> dict:
    """Aggregate career stats for one athlete across all result rows."""
    stats = {"name": name, "gold": 0, "silver": 0, "bronze": 0, "competitions": 0, "points": []}

    # Pull from results table
    if not results_df.empty and "name" in results_df.columns:
        rows = results_df[results_df["name"].str.lower() == name.lower()]
        stats["competitions"] = rows["competition_id"].nunique() if "competition_id" in rows.columns else len(rows)
        if "medal" in rows.columns:
            stats["gold"] = int((rows["medal"].str.lower() == "gold").sum())
            stats["silver"] = int((rows["medal"].str.lower() == "silver").sum())
            stats["bronze"] = int((rows["medal"].str.lower() == "bronze").sum())
        if "points" in rows.columns:
            stats["points"] = rows["points"].dropna().tolist()

    # Pull country / discipline from athletes table
    if not athletes_df.empty and "name" in athletes_df.columns:
        match = athletes_df[athletes_df["name"].str.lower() == name.lower()]
        if not match.empty:
            row = match.iloc[0]
            stats["country"] = row.get("country", "")
            stats["discipline"] = row.get("discipline", "")
            stats["rank"] = row.get("rank", "")

    return stats


def _radar_chart(stats_a: dict, stats_b: dict) -> go.Figure:
    categories = ["Gold", "Silver", "Bronze", "Competitions"]
    max_vals = {
        "Gold": max(stats_a["gold"], stats_b["gold"], 1),
        "Silver": max(stats_a["silver"], stats_b["silver"], 1),
        "Bronze": max(stats_a["bronze"], stats_b["bronze"], 1),
        "Competitions": max(stats_a["competitions"], stats_b["competitions"], 1),
    }

    def norm(s):
        return [
            s["gold"] / max_vals["Gold"],
            s["silver"] / max_vals["Silver"],
            s["bronze"] / max_vals["Bronze"],
            s["competitions"] / max_vals["Competitions"],
        ]

    fig = go.Figure()
    for stats, color in [(stats_a, "#e94560"), (stats_b, "#f5c518")]:
        vals = norm(stats)
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=stats["name"],
            line_color=color,
            fillcolor=color.replace(")", ", 0.2)").replace("rgb", "rgba") if "rgb" in color else color + "33",
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], showticklabels=False),
            bgcolor="#1a1a2e",
        ),
        showlegend=True,
        paper_bgcolor="#0e1117",
        font_color="#fafafa",
        height=400,
        margin=dict(t=20, b=20),
    )
    return fig


def _bar_comparison(stats_a: dict, stats_b: dict) -> go.Figure:
    metrics = ["gold", "silver", "bronze", "competitions"]
    labels = ["Gold", "Silver", "Bronze", "Competitions"]
    colors_a = ["#e94560"] * 4
    colors_b = ["#f5c518"] * 4

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=stats_a["name"],
        x=labels,
        y=[stats_a[m] for m in metrics],
        marker_color=colors_a,
    ))
    fig.add_trace(go.Bar(
        name=stats_b["name"],
        x=labels,
        y=[stats_b[m] for m in metrics],
        marker_color=colors_b,
    ))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#1a1a2e",
        font_color="#fafafa",
        height=350,
        margin=dict(t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def render(results_df: pd.DataFrame, athletes_df: pd.DataFrame):
    st.subheader("Head-to-Head Athlete Comparison")

    # Build name list from athletes table, fallback to results
    names = []
    if not athletes_df.empty and "name" in athletes_df.columns:
        names = sorted(athletes_df["name"].dropna().unique().tolist())
    elif not results_df.empty and "name" in results_df.columns:
        names = sorted(results_df["name"].dropna().unique().tolist())

    if len(names) < 2:
        st.info("Not enough athlete data. Run the scraper first (`python main.py scrape`).")
        return

    col1, col2 = st.columns(2)
    with col1:
        athlete_a = st.selectbox("Athlete A", names, index=0, key="h2h_a")
    with col2:
        default_b = 1 if len(names) > 1 else 0
        athlete_b = st.selectbox("Athlete B", names, index=default_b, key="h2h_b")

    if athlete_a == athlete_b:
        st.warning("Select two different athletes.")
        return

    stats_a = _get_athlete_stats(results_df, athletes_df, athlete_a)
    stats_b = _get_athlete_stats(results_df, athletes_df, athlete_b)

    # Stat cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    card_data = [
        (c1, stats_a["name"], ""),
        (c2, f"🥇 {stats_a['gold']}", "Gold"),
        (c3, f"🥈 {stats_a['silver']}", "Silver"),
        (c4, f"🥇 {stats_b['gold']}", "Gold"),
        (c5, f"🥈 {stats_b['silver']}", "Silver"),
        (c6, stats_b["name"], ""),
    ]

    col_a1, col_a2, col_a3, spacer, col_b1, col_b2, col_b3 = st.columns([2, 1, 1, 0.5, 1, 1, 2])
    for col, label, val in [
        (col_a1, "Athlete", stats_a["name"]),
        (col_a2, "Gold", stats_a["gold"]),
        (col_a3, "Silver", stats_a["silver"]),
        (col_b1, "Gold", stats_b["gold"]),
        (col_b2, "Silver", stats_b["silver"]),
        (col_b3, "Athlete", stats_b["name"]),
    ]:
        col.metric(label, val)

    st.plotly_chart(_bar_comparison(stats_a, stats_b), use_container_width=True)

    with st.expander("Radar chart"):
        st.plotly_chart(_radar_chart(stats_a, stats_b), use_container_width=True)

    # Profile cards
    st.markdown("---")
    pa, pb = st.columns(2)
    for col, stats in [(pa, stats_a), (pb, stats_b)]:
        with col:
            st.markdown(f"**{stats['name']}**")
            if stats.get("country"):
                st.markdown(f"Country: `{stats['country']}`")
            if stats.get("discipline"):
                st.markdown(f"Discipline: `{stats['discipline']}`")
            if stats.get("rank"):
                st.markdown(f"World Rank: `{stats['rank']}`")
