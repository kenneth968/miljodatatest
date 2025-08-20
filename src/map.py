import numpy as np
import pydeck as pdk
from src.constants import BASEMAP_CONFIGS, MAPBOX_TOKEN


def build_energy_map(gdf, bdf, city, view, basemap_choice):
    bdf = bdf.assign(
        kwh=gdf.groupby("building_id")["kwh"].sum().reindex(bdf["building_id"]).values,
        total_HE=gdf.groupby("building_id")["total_HE"].first().reindex(bdf["building_id"]).values,
        kwh_per_m2=gdf.groupby("building_id")["kwh_per_m2"].mean().reindex(bdf["building_id"]).values,
    )
    bdf = bdf.assign(
        radius=(np.sqrt(bdf["total_HE"].fillna(0)) * 20).clip(100, 1000),
    )
    bdf["color"] = [[200, 30, 0, 160]] * len(bdf)

    view_state = pdk.ViewState(
        latitude=view["lat"], longitude=view["lon"], zoom=view["zoom"], pitch=45
    )
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=bdf,
        get_position="[lon, lat]",
        get_elevation="kwh",
        elevation_scale=0.01,
        radius="radius",
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=bdf,
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color="color",
    )

    tooltip = {
        "html": (
            "<b>{name}</b><br/>" "Power: {kwh:.0f} kWh<br/>" "Students: {total_HE}<br/>" "Area: {area_m2:.0f} m²"
        ),
        "style": {"color": "white"},
    }

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
        return pdk.Deck(
            layers=[osm_layer, column_layer, scatter_layer],
            initial_view_state=view_state,
            tooltip=tooltip,
        )
    elif config["provider"] == "carto":
        return pdk.Deck(
            layers=[column_layer, scatter_layer],
            initial_view_state=view_state,
            map_provider="carto",
            map_style=config["style"],
            tooltip=tooltip,
        )
    else:
        kwargs = dict(
            layers=[column_layer, scatter_layer],
            initial_view_state=view_state,
            map_provider="mapbox",
            map_style=config["style"],
            tooltip=tooltip,
        )
        if MAPBOX_TOKEN:
            kwargs["api_keys"] = {"mapbox": MAPBOX_TOKEN}
        return pdk.Deck(**kwargs)
