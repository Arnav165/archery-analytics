import pandas as pd
import plotly.express as px
import streamlit as st


def render(tournaments_df: pd.DataFrame, results_df: pd.DataFrame):
    st.subheader("Tournament Browser")

    if tournaments_df.empty:
        st.info("No tournament data loaded. Run `python main.py fetch` first.")
        return

    # --- Filters ---
    st.markdown("#### Filters")
    fc1, fc2, fc3 = st.columns(3)

    with fc1:
        date_col = next((c for c in ("date_from", "date") if c in tournaments_df.columns), None)
        if date_col:
            tournaments_df[date_col] = pd.to_datetime(tournaments_df[date_col], errors="coerce")
            years = sorted(tournaments_df[date_col].dropna().dt.year.unique().tolist(), reverse=True)
            years_opts = ["All"] + [str(y) for y in years]
            selected_year = st.selectbox("Year", years_opts, key="tb_year")
        else:
            date_col = None
            selected_year = "All"

    with fc2:
        loc_col = next((c for c in ("place", "location", "venue") if c in tournaments_df.columns), None)
        if loc_col:
            locations = ["All"] + sorted(tournaments_df[loc_col].dropna().unique().tolist())
            selected_loc = st.selectbox("Location", locations, key="tb_loc")
        else:
            selected_loc = "All"

    with fc3:
        if "name" in tournaments_df.columns:
            search = st.text_input("Search name", key="tb_search")
        else:
            search = ""

    # --- Apply filters ---
    df = tournaments_df.copy()

    if selected_year != "All" and date_col:
        df = df[df[date_col].dt.year == int(selected_year)]

    if selected_loc != "All" and loc_col:
        df = df[df[loc_col] == selected_loc]

    if search and "name" in df.columns:
        df = df[df["name"].str.contains(search, case=False, na=False)]

    st.markdown(f"**{len(df)} tournament(s) found**")

    if df.empty:
        st.warning("No tournaments match the selected filters.")
        return

    # --- Tournament list ---
    display_cols = [c for c in ("name", "date_from", "date_to", "place", "country_name", "level") if c in df.columns]
    st.dataframe(df[display_cols].reset_index(drop=True), use_container_width=True)

    # --- Select one tournament to drill into ---
    if "name" in df.columns:
        selected_name = st.selectbox(
            "Select a tournament to explore results",
            df["name"].tolist(),
            key="tb_selected",
        )

        tournament_row = df[df["name"] == selected_name].iloc[0]

        st.markdown(f"### {selected_name}")
        if "date" in tournament_row.index and pd.notna(tournament_row.get("date")):
            st.markdown(f"Date: **{tournament_row['date'].strftime('%B %d, %Y')}**")
        if "location" in tournament_row.index and tournament_row.get("location"):
            st.markdown(f"Location: **{tournament_row['location']}**")

        # Filter results to this tournament
        comp_id = tournament_row.get("competition_id")
        t_results = pd.DataFrame()
        if not results_df.empty and comp_id and "competition_id" in results_df.columns:
            t_results = results_df[results_df["competition_id"] == comp_id]
        elif not results_df.empty and "name" in results_df.columns:
            t_results = results_df[results_df.get("competition_name", pd.Series()) == selected_name]

        if t_results.empty:
            st.info("No detailed results available for this tournament yet.")
        else:
            st.markdown("#### Results")
            st.dataframe(t_results.reset_index(drop=True), use_container_width=True)

            # Score distribution chart if points column exists
            if "points" in t_results.columns:
                score_df = t_results[["name", "points"]].dropna() if "name" in t_results.columns else t_results[["points"]].dropna()
                fig = px.bar(
                    score_df.sort_values("points", ascending=False).head(20),
                    x="name" if "name" in score_df.columns else score_df.index,
                    y="points",
                    title="Top 20 Scores",
                    color="points",
                    color_continuous_scale="reds",
                )
                fig.update_layout(
                    paper_bgcolor="#0e1117",
                    plot_bgcolor="#1a1a2e",
                    font_color="#fafafa",
                    height=350,
                    showlegend=False,
                    margin=dict(t=40, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Medal breakdown pie chart
            if "medal" in t_results.columns:
                medal_counts = t_results["medal"].value_counts().reset_index()
                medal_counts.columns = ["medal", "count"]
                fig2 = px.pie(
                    medal_counts,
                    names="medal",
                    values="count",
                    title="Medal Distribution",
                    color_discrete_map={"Gold": "#f5c518", "Silver": "#c0c0c0", "Bronze": "#cd7f32"},
                )
                fig2.update_layout(
                    paper_bgcolor="#0e1117",
                    font_color="#fafafa",
                    height=300,
                )
                st.plotly_chart(fig2, use_container_width=True)
