# Refactored main entrypoint for the Student Housing Energy app.
# This version emphasizes separation of concerns, modularity, and code reuse.

from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from src.constants import CITY_VIEWS
from src.data import load_data, aggregate_data
from src.kpis import compute_kpis
from src.map import build_energy_map
from src.utils import robust_z_scores


def main():
    st.set_page_config(page_title="Studentbolig Energi", layout="centered")

    # Load real data from CSV; fall back to synthetic if files are missing.
    buildings, energy, total_he, weather = load_data(use_csv=True)

    with st.container():
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("Trondheim", use_container_width=True):
            st.session_state.city = "Trondheim"
        if c2.button("Gjøvik", use_container_width=True):
            st.session_state.city = "Gjøvik"
        if c3.button("Ålesund", use_container_width=True):
            st.session_state.city = "Ålesund"

    st.session_state.basemap = "Mapbox — Streets v12"

    with st.sidebar:
        metric_label = st.radio(
            "Kolonnehøyde",
            ["Total energi", "kWh per student", "kWh per m²"],
            index=0,
        )
        filter_mode = st.radio(
            "Filter",
            ["År", "Måneder", "Måned over år"],
            index=0,
        )
        if filter_mode == "År":
            year = st.selectbox("År", [2022, 2023, 2024, 2025], index=3)
            start = pd.Timestamp(year=year, month=1, day=1)
            end = pd.Timestamp(year=year, month=12, day=31)
        elif filter_mode == "Måneder":
            months = pd.date_range("2022-01-01", "2025-12-01", freq="MS")
            start = st.selectbox("Start", months, index=len(months) - 12)
            end = st.selectbox("Slutt", months, index=len(months) - 1)
            if start > end:
                start, end = end, start
        else:
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month = st.selectbox("Måned", list(range(1, 13)), format_func=lambda x: month_names[x - 1])
            years = st.multiselect("År", [2022, 2023, 2024, 2025], default=[2025])
            if not years:
                years = [2025]

    city = st.session_state.city
    view = CITY_VIEWS[city]

    bdf = buildings.query("city == @city").copy()
    edf = (
        energy.merge(total_he, on="building_id", how="left")
              .merge(bdf[["building_id"]], on="building_id")
              .merge(weather.query("city == @city"), on="date")
    )

    if filter_mode == "År" or filter_mode == "Måneder":
        edf = edf[(edf["date"] >= pd.to_datetime(start)) & (edf["date"] <= pd.to_datetime(end))]
    else:
        edf = edf[(edf["date"].dt.month == month) & (edf["date"].dt.year.isin(years))]
    gdf = aggregate_data(edf.copy(), bdf, "Month")

    compute_kpis(edf, gdf)

    metric_map = {
        "Total energi": "kwh",
        "kWh per student": "kwh_per_student",
        "kWh per m²": "kwh_per_m2",
    }

    st.pydeck_chart(
        build_energy_map(gdf, bdf, city, view, st.session_state.basemap, metric_map[metric_label]),
        use_container_width=True,
    )

    st.subheader(f"Energi mot graddager (HDD) — {city}")
    ts_city = edf.groupby("date", as_index=False)[["kwh", "hdd_17c"]].sum().sort_values("date")
    st.line_chart(ts_city.set_index("date"), use_container_width=True)

    st.subheader("Største avvik (robust z-score)")
    top_idx = gdf["z_score"].abs().nlargest(10).index
    top = gdf.loc[top_idx, [
        "date",
        "building_id",
        "name",
        "kwh",
        "expected_kwh",
        "kwh_per_m2",
        "residual",
        "z_score",
    ]].rename(columns={
        "date": "Dato",
        "building_id": "Bygg-ID",
        "name": "Navn",
        "kwh": "kWh",
        "expected_kwh": "Forventet kWh",
        "kwh_per_m2": "kWh/m²",
        "residual": "Avvik (kWh)",
        "z_score": "Robust z-score",
    })
    st.dataframe(top, use_container_width=True)


if __name__ == "__main__":
    if "city" not in st.session_state:
        st.session_state.city = "Trondheim"
    if "basemap" not in st.session_state:
        st.session_state.basemap = "Mapbox — Custom (your style)"

    main()
