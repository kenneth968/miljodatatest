import numpy as np
import pydeck as pdk
from src.constants import BASEMAP_CONFIGS, MAPBOX_TOKEN


def z_to_color(z: float) -> list[int]:
    if z > 1.5:
        return [220, 30, 30, 200]
    if z > 0.5:
        return [250, 150, 20, 200]
    if z < -1.5:
        return [30, 80, 220, 200]
    if z < -0.5:
        return [80, 180, 250, 200]
    return [200, 200, 200, 200]


def build_energy_map(gdf, bdf, city, view, basemap_choice, metric: str = "kwh"):

    assert "lon" in bdf.columns and "lat" in bdf.columns, "bdf must contain 'lon' and 'lat' columns"
    bdf = bdf.dropna(subset=["lon", "lat"])

    # Ensure numeric and clipped Z-scores
    zs = (
        gdf.groupby("building_id")["z_score"].mean()
        .reindex(bdf["building_id"])
        .fillna(0)
        .clip(-3, 3)
    )

    bdf = bdf.assign(
        kwh=gdf.groupby("building_id")["kwh"].sum().reindex(bdf["building_id"]).values,
        total_HE=gdf.groupby("building_id")["total_HE"].first().reindex(bdf["building_id"]).values,
        kwh_per_m2=gdf.groupby("building_id")["kwh_per_m2"].mean().reindex(bdf["building_id"]).values,
        kwh_per_student=gdf.groupby("building_id")["kwh_per_student"].mean().reindex(bdf["building_id"]).values,
        z_color=[z_to_color(z) for z in zs.values],
    )

    # Metric selector
    value_field = {
        "kwh": "kwh",
        "kwh_per_student": "kwh_per_student",
        "kwh_per_m2": "kwh_per_m2",
    }.get(metric, "kwh")
    
    bdf["value"] = bdf[value_field].fillna(0)

    # Radius and color
    bdf["radius"] = (np.sqrt(bdf["total_HE"].fillna(0)) * 5).clip(30, 200)
    bdf["color"] = bdf["z_color"]

    # Filter out rows with missing values needed for visualization
    bdf = bdf.dropna(subset=["value", "lon", "lat"])

    # Convert to Python dicts for pydeck compatibility
    data_records = bdf[["lon", "lat", "value", "radius", "color"]].to_dict(orient="records")

    # View
    view_state = pdk.ViewState(
        latitude=view["lat"],
        longitude=view["lon"],
        zoom=view["zoom"],
        pitch=45
    )

    column_layer = pdk.Layer(
        "ColumnLayer",
        data=data_records,
        get_position=["lon", "lat"],
        get_elevation="value",
        elevation_scale=0.005,
        radius="radius",
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": (
            "<b>{name}</b><br/>"
            "Power: {kwh:.0f} kWh<br/>"
            "kWh/student: {kwh_per_student:.2f}<br/>"
            "kWh/m²: {kwh_per_m2:.2f}<br/>"
            "Students: {total_HE}<br/>"
            "Area: {area_m2:.0f} m²"
        ),
        "style": {"color": "white"},
    }

    config = BASEMAP_CONFIGS.get(basemap_choice, BASEMAP_CONFIGS["OpenStreetMap (no token)"])

    if config["provider"] == "osm":
        tile_layer = pdk.Layer(
            "TileLayer",
            data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            min_zoom=0,
            max_zoom=19,
            tile_size=256,
            opacity=1.0,
            pickable=False,
        )
        layers = [tile_layer, column_layer]
        return pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip=tooltip,
        )

    elif config["provider"] == "carto":
        return pdk.Deck(
            layers=[column_layer],
            initial_view_state=view_state,
            map_provider="carto",
            map_style=config["style"],
            tooltip=tooltip,
        )

    else:
        kwargs = dict(
            layers=[column_layer],
            initial_view_state=view_state,
            map_provider="mapbox",
            map_style=config["style"],
            tooltip=tooltip,
        )
        if MAPBOX_TOKEN:
            kwargs["api_keys"] = {"mapbox": MAPBOX_TOKEN}
        return pdk.Deck(**kwargs)
