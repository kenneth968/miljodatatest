from typing import Dict

MAPBOX_TOKEN: str = (
    "pk.eyJ1Ijoia2VubmV0a3MiLCJhIjoiY21lZmQ0amRvMHVvbzJrc2F5NjRlNHk1eSJ9.XosWlDVfg_n72giyeIKO3g"
)

CITY_VIEWS: Dict[str, Dict[str, float]] = {
    "Trondheim": {"lat": 63.4305, "lon": 10.3951, "zoom": 11},
    "Gjøvik":    {"lat": 60.7957, "lon": 10.6916, "zoom": 12},
    "Ålesund":   {"lat": 62.4722, "lon": 6.1495,  "zoom": 12},
}

BASEMAP_CONFIGS: Dict[str, Dict[str, str | None]] = {
    "Mapbox — Custom (your style)": {"provider": "mapbox", "style": "mapbox://styles/mapbox/standard"},
    "Mapbox — Light v11":           {"provider": "mapbox", "style": "mapbox://styles/mapbox/light-v11"},
    "Mapbox — Streets v12":         {"provider": "mapbox", "style": "mapbox://styles/mapbox/streets-v12"},
    "CARTO — Positron (no token)":  {"provider": "carto",  "style": "light"},
    "OpenStreetMap (no token)":     {"provider": "osm",    "style": None},
}
