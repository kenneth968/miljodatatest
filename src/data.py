from datetime import date
import numpy as np
import pandas as pd
import streamlit as st
from src.constants import CITY_VIEWS

@st.cache_data
def load_data():
    rng = np.random.default_rng(42)
    rows = []
    for city, v in CITY_VIEWS.items():
        for i in range(6):
            lat = v["lat"] + rng.normal(0, 0.01)
            lon = v["lon"] + rng.normal(0, 0.02)
            area = int(rng.integers(1500, 8000))
            capacity = int(rng.integers(80, 450))
            rows.append(dict(
                building_id=f"{city[:2].upper()}_{i+1}",
                city=city, name=f"{city} Studenthus {i+1}",
                lat=float(lat), lon=float(lon), area_m2=area,
                capacity_students=capacity
            ))
    buildings = pd.DataFrame(rows)

    dates = pd.date_range(end=date.today(), periods=365*3, freq="D")
    energy, occupancy, weather = [], [], []
    for _, b in buildings.iterrows():
        base = float(np.clip(b["area_m2"]/10, 150, 900))
        for d in dates:
            doy = d.timetuple().tm_yday
            temp = float(8 + 10*np.sin(2*np.pi*doy/365) + np.random.normal(0,2))
            hdd = float(max(0, 17 - temp))
            occ = int(0.8*b["capacity_students"] + np.random.normal(0, 10))
            kwh = float(base + 30*hdd + 0.6*occ + np.random.normal(0, 80))
            energy.append(dict(date=d, building_id=b.building_id, kwh=max(kwh, 0.0)))
            occupancy.append(dict(date=d, building_id=b.building_id, occupants=max(occ, 0)))
            weather.append(dict(date=d, city=b.city, temp_mean_c=temp, hdd_17c=hdd))

    weather_df = pd.DataFrame(weather).drop_duplicates(subset=["date","city"])
    return buildings, pd.DataFrame(energy), pd.DataFrame(occupancy), weather_df

def aggregate_data(edf, bdf, granularity):
    if granularity == "Day":
        out = edf
    elif granularity == "Month":
        out = (
            edf.assign(month=lambda x: x["date"].values.astype("datetime64[M]"))
              .groupby(["month", "building_id"], as_index=False)[["kwh","occupants","hdd_17c"]].sum()
              .rename(columns={"month":"date"})
        )
    elif granularity == "Year":
        out = (
            edf.assign(year=lambda x: x["date"].dt.year)
              .groupby(["year","building_id"], as_index=False)[["kwh","occupants","hdd_17c"]].sum()
              .rename(columns={"year":"date"})
        )
        out["date"] = pd.to_datetime(out["date"].astype(str) + "-01-01")
    else:
        out = edf

    out = out.merge(
        bdf[["building_id","area_m2","name","lat","lon"]],
        on="building_id",
        how="left"
    )
    out["expected_kwh"] = 30*out["hdd_17c"] + 0.5*out["occupants"]
    out["residual"] = out["kwh"] - out["expected_kwh"]
    out["kwh_per_m2"] = out["kwh"] / out["area_m2"].replace(0, np.nan)
    from src.utils import robust_z_scores
    out["z_score"] = robust_z_scores(out["residual"].to_numpy())
    return out