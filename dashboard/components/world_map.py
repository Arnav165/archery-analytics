import pandas as pd
import plotly.express as px
import pycountry
import streamlit as st


def _add_iso_alpha3(df: pd.DataFrame) -> pd.DataFrame:
    """Map country name or 3-letter NOC code to ISO alpha-3 for Plotly choropleth."""
    def lookup(name: str) -> str:
        if not name or not isinstance(name, str):
            return ""
        name = name.strip()
        # Try direct ISO lookup by alpha-3
        try:
            c = pycountry.countries.get(alpha_3=name.upper())
            if c:
                return c.alpha_3
        except Exception:
            pass
        # Try by name
        try:
            results = pycountry.countries.search_fuzzy(name)
            if results:
                return results[0].alpha_3
        except Exception:
            pass
        return ""

    df = df.copy()
    df["iso_alpha3"] = df["country"].apply(lookup)
    return df


def render(medals_df: pd.DataFrame):
    st.subheader("World Medal Map")

    if medals_df.empty:
        st.info("No medal data loaded. Run `python main.py fetch` first.")
        return

    medal_type = st.radio(
        "Medal type",
        ["total", "gold", "silver", "bronze"],
        horizontal=True,
        key="map_medal_type",
    )

    df = _add_iso_alpha3(medals_df)
    df = df[df["iso_alpha3"] != ""]

    if df.empty:
        st.warning("Could not map any country names to ISO codes.")
        return

    fig = px.choropleth(
        df,
        locations="iso_alpha3",
        color=medal_type,
        hover_name="country",
        hover_data={"gold": True, "silver": True, "bronze": True, "total": True, "iso_alpha3": False},
        color_continuous_scale=[
            [0.0, "#1a1a2e"],
            [0.3, "#16213e"],
            [0.6, "#e94560"],
            [1.0, "#f5c518"],
        ],
        title=f"Archery {medal_type.title()} Medals by Country",
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

    with st.expander("Raw medal table"):
        st.dataframe(
            medals_df.sort_values("total", ascending=False).reset_index(drop=True),
            use_container_width=True,
        )
