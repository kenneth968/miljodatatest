import os
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.set_page_config(page_title="3D Streets", layout="centered")

MAPBOX_TOKEN = "pk.eyJ1Ijoia2VubmV0a3MiLCJhIjoiY21lZmQ0amRvMHVvbzJrc2F5NjRlNHk1eSJ9.XosWlDVfg_n72giyeIKO3g"
os.environ["MAPBOX_API_KEY"] = MAPBOX_TOKEN

def generate_geo_data(rows=400, center=(41.889, 12.488), spread=(400, 400)):
    arr = np.random.randn(rows, 2) / spread + center
    return pd.DataFrame(arr, columns=["lat", "lon"])

def view_state(center=(41.889, 12.488), zoom=16, pitch=65, bearing=30):
    return pdk.ViewState(latitude=center[0], longitude=center[1], zoom=zoom, pitch=pitch, bearing=bearing)

def scatter_layer(df):
    return pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_radius=8,
        get_fill_color=[230, 70, 30, 180],
        pickable=True,
    )

def render(deck):
    c1, c2, c3 = st.columns([1,5,1])
    with c2:
        st.pydeck_chart(deck, use_container_width=True)

def main():
    st.title("Mapbox Streets with 3D Buildings")
    df = generate_geo_data()
    vs = view_state()
    layers = [scatter_layer(df)]
    deck = pdk.Deck(
        map_provider="mapbox",
        map_style="mapbox://styles/mapbox/standard",
        initial_view_state=vs,
        layers=layers,
        api_keys={"mapbox": MAPBOX_TOKEN},
        tooltip={"text": "lat: {lat}\nlon: {lon}"},
    )
    render(deck)

if __name__ == "__main__":
    main()