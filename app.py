# Refactored main entrypoint for the Student Housing Energy app.
# This version emphasizes separation of concerns, modularity, and code reuse.

from __future__ import annotations

import os
from datetime import date
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st

from src.constants import CITY_VIEWS, BASEMAP_CONFIGS, MAPBOX_TOKEN
from src.data import load_data, aggregate_data
from src.kpis import compute_kpis
from src.map import build_energy_map
from src.utils import robust_z_scores


def main():
    st.set_page_config(page_title="Studentbolig Energi", layout="centered")

    # Load real data from CSV; fall back to synthetic if files are missing.
    buildings, energy, total_he, weather = load_data(use_csv=True)

    granularity_labels = ["Måned", "År"]
    granularity_map = dict(zip(granularity_labels, ["Month", "Year"]))

    with st.container():
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
        if c1.button("Trondheim", use_container_width=True):
            st.session_state.city = "Trondheim"
        if c2.button("Gjøvik", use_container_width=True):
            st.session_state.city = "Gjøvik"
        if c3.button("Ålesund", use_container_width=True):
            st.session_state.city = "Ålesund"

        current_label = {v: k for k, v in granularity_map.items()}[st.session_state.granularity]
        chosen_label = c4.radio(
            "Detaljnivå",
            granularity_labels,
            index=granularity_labels.index(current_label),
            horizontal=True,
        )
        st.session_state.granularity = granularity_map[chosen_label]

        st.session_state.period = c5.date_input(
            "Periode", value=st.session_state.period,
            help="Velg start- og sluttdato",
        )

    st.session_state.basemap = "Mapbox — Streets v12"

    city = st.session_state.city
    view = CITY_VIEWS[city]

    bdf = buildings.query("city == @city").copy()
    edf = (
        energy.merge(total_he, on="building_id", how="left")
              .merge(bdf[["building_id"]], on="building_id")
              .merge(weather.query("city == @city"), on="date")
    )

    period_val = st.session_state.period
    if isinstance(period_val, tuple) and len(period_val) == 2:
        start, end = period_val
        edf = edf[(edf["date"] >= pd.to_datetime(start)) & (edf["date"] <= pd.to_datetime(end))]

    gdf = aggregate_data(edf.copy(), bdf, st.session_state.granularity)

    compute_kpis(edf, gdf)

    st.pydeck_chart(
        build_energy_map(gdf, bdf, city, view, st.session_state.basemap),
        use_container_width=True
    )

    granularity_label = {v: k for k, v in granularity_map.items()}[st.session_state.granularity]
    st.subheader(f"Energi mot graddager (HDD) — {city} ({granularity_label})")
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
    if "granularity" not in st.session_state:
        st.session_state.granularity = "Month"
    if "period" not in st.session_state:
        st.session_state.period = (date.today().replace(year=date.today().year - 1), date.today())
    if "basemap" not in st.session_state:
        st.session_state.basemap = "Mapbox — Custom (your style)"

    main()
