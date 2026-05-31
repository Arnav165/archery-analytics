import pandas as pd
import plotly.express as px
import pycountry
import streamlit as st

# Hand-coded overrides for NOC codes that differ from ISO alpha-3
NOC_TO_ISO = {
    "USA": "USA", "GBR": "GBR", "GER": "DEU", "FRG": "DEU", "GDR": "DEU",
    "URS": "RUS", "EUN": "RUS", "RUS": "RUS", "CHN": "CHN", "KOR": "KOR",
    "FRA": "FRA", "AUS": "AUS", "ITA": "ITA", "NED": "NLD", "BEL": "BEL",
    "SWE": "SWE", "FIN": "FIN", "NOR": "NOR", "DEN": "DNK", "SUI": "CHE",
    "POL": "POL", "HUN": "HUN", "TCH": "CZE", "YUG": "SRB", "BUL": "BGR",
    "ROU": "ROU", "IRI": "IRN", "JPN": "JPN", "IND": "IND", "PRK": "PRK",
    "TPE": "TWN", "MEX": "MEX", "BRA": "BRA", "ARG": "ARG", "COL": "COL",
    "TUR": "TUR", "ESP": "ESP", "UKR": "UKR", "BLR": "BLR", "KAZ": "KAZ",
    "MAS": "MYS", "INA": "IDN", "THA": "THA", "PHI": "PHL",
}


def _noc_to_iso(noc: str) -> str:
    if noc in NOC_TO_ISO:
        return NOC_TO_ISO[noc]
    try:
        results = pycountry.countries.search_fuzzy(noc)
        return results[0].alpha_3
    except Exception:
        return ""


def render(medals_df: pd.DataFrame):
    st.subheader("World Medal Map")
    st.caption("Olympic Archery medals by country · 1900–2016")

    if medals_df.empty:
        st.info("No data yet — run `python main.py fetch` first.")
        return

    medal_type = st.radio(
        "Show",
        ["total", "gold", "silver", "bronze"],
        horizontal=True,
        key="map_medal_type",
    )

    df = medals_df.copy()
    df["iso3"] = df["noc"].apply(_noc_to_iso)
    df = df[df["iso3"] != ""]

    fig = px.choropleth(
        df,
        locations="iso3",
        color=medal_type,
        hover_name="country",
        hover_data={
            "gold": True, "silver": True, "bronze": True,
            "total": True, "iso3": False, "noc": True,
        },
        color_continuous_scale=[
            [0.0, "#1a1a2e"],
            [0.3, "#16213e"],
            [0.6, "#e94560"],
            [1.0, "#f5c518"],
        ],
        title=f"Olympic Archery — {medal_type.title()} Medals",
    )
    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        coloraxis_colorbar=dict(title=medal_type.title()),
        margin=dict(l=0, r=0, t=40, b=0),
        height=500,
        paper_bgcolor="#0e1117",
        font_color="#fafafa",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Top-10 bar chart
    top = df.nlargest(10, medal_type)[["country", "gold", "silver", "bronze", "total"]]
    fig2 = px.bar(
        top,
        x="country", y=["gold", "silver", "bronze"],
        title="Top 10 Countries",
        color_discrete_map={"gold": "#f5c518", "silver": "#c0c0c0", "bronze": "#cd7f32"},
        barmode="stack",
    )
    fig2.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#1a1a2e",
        font_color="#fafafa", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Full medal table"):
        st.dataframe(
            medals_df.sort_values("total", ascending=False).reset_index(drop=True),
            use_container_width=True,
        )
