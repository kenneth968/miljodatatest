from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st

from src.constants import CITY_VIEWS


# ---------------------------------------------------------------------------
# Synthetic fallback --------------------------------------------------------
# ---------------------------------------------------------------------------

def _load_synthetic() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate synthetic demo data.

    Returns
    -------
    buildings : pd.DataFrame
        Static information about each building/project.
    energy : pd.DataFrame
        Daily energy use per building.
    total_he : pd.DataFrame
        Static capacity (number of students) per building.
    weather : pd.DataFrame
        Daily weather for each city.
    """
    rng = np.random.default_rng(42)
    rows = []
    for city, v in CITY_VIEWS.items():
        for i in range(6):
            lat = v["lat"] + rng.normal(0, 0.01)
            lon = v["lon"] + rng.normal(0, 0.02)
            area = int(rng.integers(1500, 8000))
            capacity = int(rng.integers(80, 450))
            rows.append(
                dict(
                    building_id=f"{city[:2].upper()}_{i+1}",
                    city=city,
                    name=f"{city} Studenthus {i+1}",
                    lat=float(lat),
                    lon=float(lon),
                    area_m2=area,
                    capacity_students=capacity,
                )
            )
    buildings = pd.DataFrame(rows)
    total_he = buildings[["building_id", "capacity_students"]].rename(
        columns={"capacity_students": "total_HE"}
    )

    dates = pd.date_range(end=date.today(), periods=365 * 3, freq="D")
    energy, weather = [], []
    for _, b in buildings.iterrows():
        base = float(np.clip(b["area_m2"] / 10, 150, 900))
        for d in dates:
            doy = d.timetuple().tm_yday
            temp = float(8 + 10 * np.sin(2 * np.pi * doy / 365) + rng.normal(0, 2))
            hdd = float(max(0, 17 - temp))
            occ = int(0.8 * b["capacity_students"] + rng.normal(0, 10))
            kwh = float(base + 30 * hdd + 0.6 * occ + rng.normal(0, 80))
            energy.append(
                dict(date=d, building_id=b.building_id, kwh=max(kwh, 0.0))
            )
            weather.append(
                dict(date=d, city=b.city, temp_mean_c=temp, hdd_17c=hdd)
            )

    weather_df = pd.DataFrame(weather).drop_duplicates(subset=["date", "city"])
    return buildings, pd.DataFrame(energy), total_he, weather_df


# ---------------------------------------------------------------------------
# CSV ingestion -------------------------------------------------------------
# ---------------------------------------------------------------------------

def _load_from_csv(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load project, weather and energy data from CSV files."""

    static_path = data_dir / "static_data.csv"
    temp_path = data_dir / "temperature_data.csv"
    energy_path = data_dir / "Electricity_data.csv"

    # --- Static project information ---------------------------------------
    static_df = pd.read_csv(static_path, sep=",", encoding="utf-8-sig")
    buildings = static_df.rename(
        columns={
            "project_id": "building_id",
            "project_name": "name",
            "Total_BRA": "area_m2",
            "total_HE": "capacity_students",
        }
    )
    buildings["building_id"] = buildings["building_id"].astype(str)
    buildings["name"] = buildings["name"].str.strip()
    for col in ["lat", "lon"]:
        buildings[col] = pd.to_numeric(buildings[col], errors="coerce")
    buildings = buildings[
        [
            "building_id",
            "city",
            "name",
            "year_built",
            "lat",
            "lon",
            "area_m2",
            "capacity_students",
        ]
    ]
    total_he = buildings[["building_id", "capacity_students"]].rename(
        columns={"capacity_students": "total_HE"}
    )

    # --- Weather data -----------------------------------------------------
    weather_raw = pd.read_csv(temp_path, sep=",", encoding="utf-8-sig")
    month_map = {
        "jan": "Jan",
        "feb": "Feb",
        "mar": "Mar",
        "apr": "Apr",
        "mai": "May",
        "jun": "Jun",
        "jul": "Jul",
        "aug": "Aug",
        "sep": "Sep",
        "okt": "Oct",
        "nov": "Nov",
        "des": "Dec",
    }

    def _parse_time(val: str) -> pd.Timestamp:
        m, y = val.split(".")
        m_eng = month_map.get(m.lower(), m)
        return pd.to_datetime(f"{m_eng} {y}", format="%b %y")

    weather = weather_raw.rename(
        columns={"City": "city", "Time": "time", "Temperature": "temp_mean_c"}
    )
    weather["date"] = weather["time"].apply(_parse_time)
    weather["days_in_month"] = weather["date"].dt.days_in_month
    weather["hdd_17c"] = (
        (17 - weather["temp_mean_c"]).clip(lower=0) * weather["days_in_month"]
    )
    weather = weather[["city", "date", "temp_mean_c", "hdd_17c"]]

    # --- Energy usage -----------------------------------------------------
    energy_raw = pd.read_csv(
        energy_path,
        sep=";",
        encoding="utf-8-sig",
        decimal=",",
        thousands=" ",
    )
    energy_raw.columns = [c.strip() for c in energy_raw.columns]
    energy_raw["project_name"] = energy_raw["project_name"].str.strip()
    energy_raw["City"] = energy_raw["City"].str.title().str.strip()

    month_cols = [
        "Jan_KwH",
        "Feb_KwH",
        "Mar_KwH",
        "Apr__KwH",
        "may__KwH",
        "Jun_KwH",
        "Jul_KwH",
        "Aug_KwH",
        "Sep_KwH",
        "Oct_KwH",
        "Nov_KwH",
        "Dec_KwH",
    ]
    month_numbers = {col: i + 1 for i, col in enumerate(month_cols)}

    energy = (
        energy_raw.melt(
            id_vars=["project_name", "City", "Year"],
            value_vars=month_cols,
            var_name="month",
            value_name="kwh",
        )
        .assign(month=lambda x: x["month"].map(month_numbers))
    )
    # Ensure energy values are numeric before further calculations
    energy["kwh"] = pd.to_numeric(energy["kwh"], errors="coerce")
    energy = energy.dropna(subset=["kwh"])
    energy["date"] = pd.to_datetime(
        dict(year=energy["Year"], month=energy["month"], day=1)
    )
    energy = energy.rename(columns={"project_name": "name", "City": "city"})
    energy = energy.merge(
        buildings[["building_id", "name", "city"]],
        on=["name", "city"],
        how="left",
    )
    energy = energy.dropna(subset=["building_id"])
    energy = energy[["date", "building_id", "kwh"]]

    return buildings, energy, total_he, weather


# ---------------------------------------------------------------------------
# Public API ---------------------------------------------------------------
# ---------------------------------------------------------------------------

@st.cache_data
def load_data(use_csv: bool = False, data_dir: Path | str | None = None):
    """Load data either from CSV files or using the synthetic fallback.

    Parameters
    ----------
    use_csv : bool, default False
        Whether to load data from CSV files.
    data_dir : Path | str | None, optional
        Directory containing the CSV files. If ``None`` the function will
        look for a ``.data`` folder first and fall back to ``data``.
    """
    data_path = Path(data_dir) if data_dir else Path(".data")
    if not data_path.exists():
        data_path = Path("data")
    if use_csv:
        return _load_from_csv(data_path)
    return _load_synthetic()


def aggregate_data(edf: pd.DataFrame, bdf: pd.DataFrame, granularity: str) -> pd.DataFrame:
    if granularity == "Month":
        out = (
            edf.assign(month=lambda x: x["date"].values.astype("datetime64[M]"))
               .groupby(["month", "building_id"], as_index=False)
               .agg({"kwh": "sum", "hdd_17c": "sum", "total_HE": "first"})
               .rename(columns={"month": "date"})
        )
    elif granularity == "Year":
        out = (
            edf.assign(year=lambda x: x["date"].dt.year)
               .groupby(["year", "building_id"], as_index=False)
               .agg({"kwh": "sum", "hdd_17c": "sum", "total_HE": "first"})
               .rename(columns={"year": "date"})
        )
        out["date"] = pd.to_datetime(out["date"].astype(str) + "-01-01")
    else:
        out = edf

    out = out.merge(
        bdf[["building_id", "area_m2", "name", "lat", "lon"]],
        on="building_id",
        how="left",
    )
    # Ensure all numeric columns are proper numbers.  When the input data
    # contains ``pd.NA`` or string representations of numbers, pandas can give
    # them an ``object`` dtype which breaks arithmetic operations (e.g. when
    # computing the residual below).  Coerce everything to floats first so that
    # subtraction works reliably.
    for col in ["kwh", "hdd_17c", "total_HE", "area_m2"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["expected_kwh"] = 30 * out["hdd_17c"] + 0.5 * out["total_HE"]
    out["residual"] = out["kwh"] - out["expected_kwh"]
    out["kwh_per_m2"] = out["kwh"] / out["area_m2"].replace(0, np.nan)
    out["kwh_per_student"] = out["kwh"] / out["total_HE"].replace(0, np.nan)
    from src.utils import robust_z_scores
    out["z_score"] = robust_z_scores(out["residual"].to_numpy())
    return out

