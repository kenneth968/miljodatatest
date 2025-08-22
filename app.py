# Refactored main entrypoint for the Student Housing Energy app.
# This version emphasizes separation of concerns, modularity, and code reuse.

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.constants import CITY_VIEWS
from src.data import load_data, aggregate_data
from src.kpis import compute_kpis
from src.map import build_energy_map


def main():
    st.set_page_config(page_title="Studentbolig Energi", layout="wide")

    # Load real data from CSV; fall back to synthetic if files are missing.
    buildings, energy, total_he, weather = load_data(use_csv=True)
    # Drop projects that have no associated energy readings
    buildings = buildings[buildings["building_id"].isin(energy["building_id"].unique())]
    total_he = total_he[total_he["building_id"].isin(buildings["building_id"])]
    years = sorted(energy["date"].dt.year.unique())

    with st.container():
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("Trondheim", use_container_width=True):
            st.session_state.city = "Trondheim"
        if c2.button("Gjøvik", use_container_width=True):
            st.session_state.city = "Gjøvik"
        if c3.button("Ålesund", use_container_width=True):
            st.session_state.city = "Ålesund"

    st.session_state.basemap = "Mapbox — Streets v12"

    city = st.session_state.city
    view = CITY_VIEWS[city]
    bdf = buildings.query("city == @city").copy()

    # Initialise session defaults for filters and selection
    if "metric_label" not in st.session_state:
        st.session_state.metric_label = "Total energi"
    if "year" not in st.session_state:
        st.session_state.year = int(max(years))
    if "month" not in st.session_state:
        st.session_state.month = 0  # 0 => all months
    if "granularity" not in st.session_state:
        st.session_state.granularity = "Month"
    if (
        "selected_projects" not in st.session_state
        or not set(st.session_state.selected_projects).issubset(set(bdf["name"]))
    ):
        st.session_state.selected_projects = bdf["name"].tolist()

    # Build city-level datasets
    edf_all = (
        energy.merge(total_he, on="building_id", how="left")
              .merge(bdf[["building_id"]], on="building_id")
              .merge(weather.query("city == @city"), on="date")
    )

    edf = edf_all[edf_all["date"].dt.year == st.session_state.year]
    if st.session_state.month != 0:
        edf = edf[edf["date"].dt.month == st.session_state.month]

    gdf = aggregate_data(edf.copy(), bdf, st.session_state.granularity)

    # Apply project selection
    bdf_sel = bdf[bdf["name"].isin(st.session_state.selected_projects)].copy()
    edf_sel = edf[edf["building_id"].isin(bdf_sel["building_id"])]
    gdf_sel = gdf[gdf["building_id"].isin(bdf_sel["building_id"])]

    compute_kpis(edf_sel, gdf_sel)

    # Layout: filters on the left, map in the centre, projects on the right
    left, map_col, right = st.columns([1, 3, 1])

    with left:
        st.session_state.metric_label = st.radio(
            "Kolonnehøyde",
            ["Total energi", "kWh per student", "kWh per m²"],
            index=["Total energi", "kWh per student", "kWh per m²"].index(
                st.session_state.metric_label
            ),
        )
        st.session_state.year = st.radio(
            "År",
            years,
            index=years.index(st.session_state.year),
        )
        month_names = [
            "Alle",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "Mai",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Okt",
            "Nov",
            "Des",
        ]
        st.session_state.month = st.radio(
            "Måned",
            list(range(13)),
            index=st.session_state.month,
            format_func=lambda i: month_names[i],
        )
        st.session_state.granularity = st.radio(
            "Month/Year",
            ["Month", "Year"],
            index=["Month", "Year"].index(st.session_state.granularity),
        )

    metric_map = {
        "Total energi": "kwh",
        "kWh per student": "kwh_per_student",
        "kWh per m²": "kwh_per_m2",
    }

    with right:
        st.session_state.selected_projects = st.multiselect(
            "Prosjekter",
            bdf["name"].tolist(),
            default=st.session_state.selected_projects,
        )

    with map_col:
        st.pydeck_chart(
            build_energy_map(
                gdf_sel,
                bdf_sel,
                city,
                view,
                st.session_state.basemap,
                metric_map[st.session_state.metric_label],
            ),
            use_container_width=True,
        )

    st.subheader(f"Tidsserie — {st.session_state.metric_label}")
    gdf_all = aggregate_data(edf_all.copy(), bdf, st.session_state.granularity)
    gdf_all_sel = gdf_all[gdf_all["building_id"].isin(bdf_sel["building_id"])]
    ts_energy = (
        gdf_all_sel.groupby("date", as_index=False)[metric_map[st.session_state.metric_label]]
        .sum()
        .rename(columns={metric_map[st.session_state.metric_label]: "energy"})
        .sort_values("date")
    )
    temp_ts = weather.query("city == @city").copy()
    if st.session_state.granularity == "Year":
        temp_ts = (
            temp_ts.assign(year=temp_ts["date"].dt.year)
                   .groupby("year", as_index=False)["temp_mean_c"].mean()
                   .assign(date=lambda x: pd.to_datetime(x["year"].astype(str) + "-01-01"))
                   .sort_values("date")[ ["date", "temp_mean_c"] ]
        )
    else:
        temp_ts = temp_ts.sort_values("date")[ ["date", "temp_mean_c"] ]

    date_format = "%Y" if st.session_state.granularity == "Year" else "%b %Y"

    temp_line = alt.Chart(temp_ts).mark_line(color="orange", opacity=0.3).encode(
        x=alt.X("date:T", axis=alt.Axis(format=date_format)),
        y=alt.Y("temp_mean_c:Q", axis=alt.Axis(title="Temperatur (°C)"))
    )
    energy_line = alt.Chart(ts_energy).mark_line(color="steelblue").encode(
        x=alt.X("date:T", axis=alt.Axis(format=date_format)),
        y=alt.Y("energy:Q", axis=alt.Axis(title=st.session_state.metric_label))
    )
    chart = alt.layer(temp_line, energy_line).resolve_scale(y="independent")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Topp tre prosjekter (robust z-score)")
    top_idx = gdf_sel["z_score"].abs().nlargest(3).index
    top = gdf_sel.loc[top_idx, [
        "date",
        "building_id",
        "name",
        "kwh",
        "expected_kwh",
        "kwh_per_m2",
        "residual",
        "z_score",
    ]].rename(
        columns={
            "date": "Dato",
            "building_id": "Bygg-ID",
            "name": "Navn",
            "kwh": "kWh",
            "expected_kwh": "Forventet kWh",
            "kwh_per_m2": "kWh/m²",
            "residual": "Avvik (kWh)",
            "z_score": "Robust z-score",
        }
    )
    st.dataframe(top, use_container_width=True)


if __name__ == "__main__":
    if "city" not in st.session_state:
        st.session_state.city = "Trondheim"
    if "basemap" not in st.session_state:
        st.session_state.basemap = "Mapbox — Custom (your style)"

    main()

