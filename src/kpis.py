"""Key performance indicators for the Streamlit dashboard.

This module previously displayed total energy, average kWh/m², average
heating degree days and a count of large z-score deviations.  The new
design removes the HDD and z-score metrics and replaces them with
`kWh per student` and a compact visual representation of the mean
temperature.
"""

from __future__ import annotations

import pandas as pd
import altair as alt
import streamlit as st


def _temperature_chart(mean_temp: float) -> alt.Chart:
    """Return a tiny horizontal gradient bar with a marker for temperature.

    The bar covers the range -10 °C to +30 °C, colouring from dark red to
    dark green.  A white dot marks the mean temperature.
    """

    domain = [-10, 30]
    base = pd.DataFrame({"temp": domain})

    bar = (
        alt.Chart(base)
        .mark_rect(height=20)
        .encode(
            x=alt.X(
                "temp",
                scale=alt.Scale(domain=domain),
                axis=alt.Axis(values=[-10, 0, 10, 20, 30], title=None),
            ),
            color=alt.Color(
                "temp",
                scale=alt.Scale(domain=domain, range=["darkred", "darkgreen"]),
                legend=None,
            ),
        )
        .properties(width=100, height=20)
    )

    point = (
        alt.Chart(pd.DataFrame({"temp": [mean_temp]}))
        .mark_point(color="white", size=50)
        .encode(x="temp")
    )

    return bar + point


def compute_kpis(edf, gdf) -> None:
    """Display KPI metrics for the filtered dataset."""

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Totalt energiforbruk (kWh)", f"{gdf['kwh'].sum():,.0f}")

    with k2:
        st.metric("Gjennomsnittlig kWh/m²", f"{gdf['kwh_per_m2'].mean():.1f}")

    with k3:
        st.metric("kWh per student", f"{gdf['kwh_per_student'].mean():.1f}")

    with k4:
        mean_temp = 17 - edf["hdd_17c"].mean()
        st.caption("Gjennomsnittlig temperatur (°C)")
        st.altair_chart(_temperature_chart(mean_temp), use_container_width=False)

