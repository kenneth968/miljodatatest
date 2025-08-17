import numpy as np
import pandas as pd
import pydeck as pdk
from src.constants import BASEMAP_CONFIGS, MAPBOX_TOKEN

def z_to_color(z: float) -> list[int]:
    if z > 1.5:   return [220, 30, 30, 200]
    if z > 0.5:   return [250, 150, 20, 200]
    if z < -1.5:  return [30, 80, 220, 200]
    if z < -0.5:  return [80, 180, 250, 200]
    return [200, 200, 200, 200]

def build_energy_map(gdf, bdf, city, view, basemap_choice):
    zs = gdf.groupby("building_id")["z_score"].mean().reindex(bdf["building_id"]).fillna(0).clip(-3, 3)
    bdf = bdf.assign(
        kwh_per_m2=gdf.groupby("building_id")["kwh_per_m2"].mean().reindex(bdf["building_id"]).values,
        z_color=[z_to_color(z) for z in zs.values],
        radius=(bdf["area_m2"] / 5).clip(150, 800)
    )

    view_state = pdk.ViewState(latitude=view["lat"], longitude=view["lon"], zoom=view["zoom"], pitch=45)
    points_layer = pdk.Layer(
        "ScatterplotLayer",
        data=bdf,
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color="z_color",
        pickable=True,
    )

    config = BASEMAP_CONFIGS.get(basemap_choice, BASEMAP_CONFIGS["OpenStreetMap (no token)"])
    if config["provider"] == "osm":
        osm_layer = pdk.Layer(
            "TileLayer",
            data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            min_zoom=0,
            max_zoom=19,
            tile_size=256,
            opacity=1.0,
            pickable=False,
        )
        return pdk.Deck(layers=[osm_layer, points_layer], initial_view_state=view_state)
    elif config["provider"] == "carto":
        return pdk.Deck(
            layers=[points_layer],
            initial_view_state=view_state,
            map_provider="carto",
            map_style=config["style"],
        )
    else:
        kwargs = dict(
            layers=[points_layer],
            initial_view_state=view_state,
            map_provider="mapbox",
            map_style=config["style"],
        )
        if MAPBOX_TOKEN:
            kwargs["api_keys"] = {"mapbox": MAPBOX_TOKEN}
        return pdk.Deck(**kwargs)