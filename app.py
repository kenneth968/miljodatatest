# Refactored main entrypoint for the Student Housing Energy app.
# This version emphasizes separation of concerns, modularity, and code reuse.

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.constants import CITY_VIEWS
from src.data import load_data, aggregate_data
from src.kpis import compute_kpis
from src.map import build_energy_map, z_to_color


def main():
    st.set_page_config(page_title="Studentbolig Energi", layout="wide")

    # Load real data from CSV; fall back to synthetic if files are missing.
    buildings, energy, total_he, weather = load_data(use_csv=True)
    # Drop projects that have no associated energy readings
    buildings = buildings[buildings["building_id"].isin(energy["building_id"].unique())]
    total_he = total_he[total_he["building_id"].isin(buildings["building_id"])]
    years = sorted(energy["date"].dt.year.unique())

    st.session_state.city = st.selectbox(
        "City",
        list(CITY_VIEWS),
        index=list(CITY_VIEWS).index(st.session_state.city),
    )

    st.session_state.basemap = "Mapbox — Streets v12"

    city = st.session_state.city
    view = CITY_VIEWS[city]
    bdf = buildings.query("city == @city").copy()

    # Initialise session defaults for filters
    if "metric_label" not in st.session_state:
        st.session_state.metric_label = "Total energi"
    if "year" not in st.session_state:
        st.session_state.year = int(max(years))
    if "month" not in st.session_state:
        st.session_state.month = 0  # 0 => all months
    if "granularity" not in st.session_state:
        st.session_state.granularity = "Month"

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

    compute_kpis(edf, gdf)

    # Layout: filters on the left and map in the centre
    left, map_col = st.columns([1, 4])

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

    with map_col:
        st.pydeck_chart(
            build_energy_map(
                gdf,
                bdf,
                city,
                view,
                st.session_state.basemap,
                metric_map[st.session_state.metric_label],
            ),
            use_container_width=True,
        )

        legend_z = [2, 1, 0, -1, -2]
        legend_labels = [
            "> 1.5",
            "0.5 to 1.5",
            "-0.5 to 0.5",
            "-1.5 to -0.5",
            "< -1.5",
        ]
        legend_colors = [
            "#%02x%02x%02x" % tuple(z_to_color(z)[:3]) for z in legend_z
        ]
        legend_df = pd.DataFrame({"label": legend_labels, "color": legend_colors})
        legend_chart = (
            alt.Chart(legend_df)
            .mark_square(size=200)
            .encode(
                y=alt.Y("label:N", axis=alt.Axis(title="Robust z-score"), sort=None),
                color=alt.Color("color:N", scale=None, legend=None),
            )
            .properties(width=100, height=100)
        )
        st.altair_chart(legend_chart, use_container_width=False)

    st.subheader(f"Tidsserie — {st.session_state.metric_label}")
    gdf_all = aggregate_data(edf_all.copy(), bdf, st.session_state.granularity)
    ts_energy = (
        gdf_all.groupby("date", as_index=False)[metric_map[st.session_state.metric_label]]
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

    st.subheader("Klima vs energiforbruk")
    climate_metric = st.radio(
        "Klimavariabel",
        ["temp_mean_c", "hdd_17c"],
        format_func=lambda v: "Temperatur (°C)" if v == "temp_mean_c" else "HDD₁₇ (graddager)",
    )
    corr_df = (
        edf.groupby("date", as_index=False)
        .agg({"kwh": "sum", "temp_mean_c": "mean", "hdd_17c": "mean"})
    )
    scatter = (
        alt.Chart(corr_df)
        .mark_circle(size=60, opacity=0.6)
        .encode(
            x=alt.X(
                f"{climate_metric}:Q",
                title="Temperatur (°C)" if climate_metric == "temp_mean_c" else "HDD₁₇ (graddager)",
            ),
            y=alt.Y("kwh:Q", title="kWh"),
            tooltip=["date:T", "kwh:Q", "temp_mean_c:Q", "hdd_17c:Q"],
        )
    )
    trend = scatter.transform_regression(climate_metric, "kwh").mark_line(color="firebrick")
    st.altair_chart(scatter + trend, use_container_width=True)

    st.subheader("Topp tre prosjekter (robust z-score)")
    top_idx = gdf["z_score"].abs().nlargest(3).index
    top = gdf.loc[top_idx, [
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

