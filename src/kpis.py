import streamlit as st
import numpy as np


def compute_kpis(edf, gdf):
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Totalt energiforbruk (kWh)", f"{gdf['kwh'].sum():,.0f}")
    with k2:
        st.metric("Gjennomsnittlig kWh/m²", f"{gdf['kwh_per_m2'].mean():.1f}")
    with k3:
        st.metric("Gjennomsnittlig HDD/dag", f"{edf['hdd_17c'].mean():.1f}")
    with k4:
        st.metric("Antall avvik (|z|≥3)", f"{(gdf['z_score'].abs() >= 3).sum()}")

