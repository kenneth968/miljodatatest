"""Key performance indicators for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as st


def compute_kpis(edf, gdf) -> None:
    """Display KPI metrics for the filtered dataset.

    The dashboard highlights energy usage together with weather-driven
    context.  Temperature was previously visualised as a small chart; in
    this revision we instead expose the values directly so they are easier
    to compare at a glance.
    """

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric("Totalt energiforbruk (kWh)", f"{gdf['kwh'].sum():,.0f}")

    with k2:
        st.metric("Gjennomsnittlig kWh/m²", f"{gdf['kwh_per_m2'].mean():.1f}")

    with k3:
        st.metric("kWh per student", f"{gdf['kwh_per_student'].mean():.1f}")

    with k4:
        mean_temp = edf["temp_mean_c"].mean()
        st.metric("Temperatur (°C)", f"{mean_temp:.1f}")

    with k5:
        mean_hdd = edf["hdd_17c"].mean()
        st.metric("HDD₁₇ (graddager)", f"{mean_hdd:.1f}")
