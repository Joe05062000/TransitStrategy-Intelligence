"""Builds the master NTD dataset for the three case-study agencies and computes
the consulting KPIs used throughout the app.

All figures originate from the real NTD TS2.1 workbook (see src/ntd_loader.py).
Nothing in this module invents, estimates, or interpolates values: KPI formulas
only divide/sum fields that are actually present in the source file, and a
division is left as NaN (never silently zeroed) whenever its denominator is
missing or zero.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ntd_loader import METRIC_SHEETS, find_workbook, load_long

# NTD ID -> short display name for the three case-study agencies.
TARGET_AGENCIES: dict[int, str] = {
    90154: "LA Metro",
    90019: "Sacramento RT",
    90003: "BART",
}

# Mode code -> consulting-friendly mode group. Agencies with very different
# fixed-guideway shares (e.g. BART is all rail, Sacramento RT mixes rail/bus)
# should only be compared within the same mode group, never at the raw
# all-modes dollar level, per the engagement's benchmarking rules.
MODE_GROUPS: dict[str, str] = {
    "HR": "Rail", "LR": "Rail", "CR": "Rail", "MG": "Rail", "YR": "Rail",
    "SR": "Rail", "CC": "Rail", "IP": "Rail", "TR": "Rail", "AR": "Rail",
    "MB": "Bus", "RB": "Bus", "CB": "Bus", "TB": "Bus",
    "DR": "Demand Response", "VP": "Demand Response", "DT": "Demand Response",
    "PB": "Demand Response", "JT": "Demand Response",
    "FB": "Ferry",
}

MODE_LABELS: dict[str, str] = {
    "HR": "Heavy Rail", "LR": "Light Rail", "CR": "Commuter Rail",
    "MG": "Monorail / Automated Guideway", "YR": "Hybrid Rail", "SR": "Streetcar",
    "CC": "Cable Car", "IP": "Inclined Plane", "TR": "Aerial Tramway",
    "AR": "Alaska Railroad", "MB": "Bus", "RB": "Bus Rapid Transit",
    "CB": "Commuter Bus", "TB": "Trolleybus", "DR": "Demand Response",
    "VP": "Vanpool", "DT": "Demand Response Taxi", "PB": "Publico",
    "JT": "Jitney", "FB": "Ferryboat",
}

# Metric columns carried through every calculation.
METRICS = [
    "OpExp Total", "OpExp VO", "OpExp VM", "OpExp NVM", "OpExp GA",
    "Fares", "DRM", "VOMS", "VRM", "VRH", "UPT", "PMT",
]

YEARS = list(range(2015, 2026))


@st.cache_data(show_spinner="Loading NTD source data...")
def load_master() -> pd.DataFrame:
    """One row per (agency, mode, type of service, year) with every metric as
    its own column, restricted to the three case-study agencies."""
    path = find_workbook()
    ntd_ids = tuple(TARGET_AGENCIES.keys())

    frames = []
    for sheet in METRIC_SHEETS:
        long_df = load_long(sheet, path)
        frames.append(long_df[long_df["NTD ID"].isin(ntd_ids)])
    all_long = pd.concat(frames, ignore_index=True)

    index_cols = ["NTD ID", "Agency Name", "Mode_Status", "Mode", "Type of Service", "year"]
    wide = (
        all_long.pivot_table(index=index_cols, columns="metric", values="value", aggfunc="first")
        .reset_index()
    )
    wide["agency"] = wide["NTD ID"].map(TARGET_AGENCIES)
    wide["mode_group"] = wide["Mode"].map(MODE_GROUPS).fillna("Other")
    wide["mode_label"] = wide["Mode"].map(MODE_LABELS).fillna(wide["Mode"])
    for m in METRICS:
        if m not in wide.columns:
            wide[m] = pd.NA
    return wide


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Division that returns NaN (never a fabricated 0) when the denominator
    is missing or zero."""
    denom = denominator.where(denominator != 0)
    return numerator / denom


def add_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Append the standard KPI columns to an already-aggregated metrics frame."""
    out = df.copy()
    out["cost_per_trip"] = _safe_div(out["OpExp Total"], out["UPT"])
    out["cost_per_vrm"] = _safe_div(out["OpExp Total"], out["VRM"])
    out["cost_per_vrh"] = _safe_div(out["OpExp Total"], out["VRH"])
    out["trips_per_vrh"] = _safe_div(out["UPT"], out["VRH"])
    out["trips_per_vrm"] = _safe_div(out["UPT"], out["VRM"])
    out["farebox_recovery"] = _safe_div(out["Fares"], out["OpExp Total"])
    out["avg_trip_length_mi"] = _safe_div(out["PMT"], out["UPT"])
    out["subsidy_per_trip"] = _safe_div(out["OpExp Total"] - out["Fares"], out["UPT"])
    out["fare_per_trip"] = _safe_div(out["Fares"], out["UPT"])
    return out


@st.cache_data(show_spinner=False)
def agency_year_kpis() -> pd.DataFrame:
    """Agency-level totals (summed across every *operating* mode) with KPIs,
    one row per agency per year. This is the "all modes combined" view used
    in the Executive Overview — useful for an agency's own trend over time,
    but not for cross-agency dollar comparisons (see mode_group_year_kpis)."""
    df = load_master()
    operating = df[df["Mode_Status"] == "Operating"]
    agg = operating.groupby(["agency", "NTD ID", "year"], as_index=False)[METRICS].sum(min_count=1)
    return add_kpis(agg).sort_values(["agency", "year"])


@st.cache_data(show_spinner=False)
def mode_group_year_kpis() -> pd.DataFrame:
    """Agency x mode-group x year totals with KPIs. This is the view that
    supports fair peer benchmarking (rail-to-rail, bus-to-bus)."""
    df = load_master()
    operating = df[df["Mode_Status"] == "Operating"]
    agg = operating.groupby(
        ["agency", "NTD ID", "mode_group", "year"], as_index=False
    )[METRICS].sum(min_count=1)
    return add_kpis(agg).sort_values(["agency", "mode_group", "year"])


def add_yoy_changes(df: pd.DataFrame, group_cols: list[str], value_cols: list[str]) -> pd.DataFrame:
    """Adds `<col>_yoy_pct` columns: percent change vs. the prior year within
    each group. Requires `df` to already be sorted/groupable by `year`."""
    out = df.sort_values(group_cols + ["year"]).copy()
    for col in value_cols:
        out[f"{col}_yoy_pct"] = out.groupby(group_cols)[col].pct_change() * 100
    return out


def cagr(first_value: float, last_value: float, n_years: int) -> float | None:
    """Compound annual growth rate between two points, in percent. Returns
    None if it cannot be computed from the real inputs (e.g. non-positive
    values or zero elapsed years) rather than fabricating a number."""
    if first_value is None or last_value is None or n_years <= 0:
        return None
    if pd.isna(first_value) or pd.isna(last_value):
        return None
    if first_value <= 0 or last_value <= 0:
        return None
    return ((last_value / first_value) ** (1 / n_years) - 1) * 100
