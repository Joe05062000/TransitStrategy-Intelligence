"""Financial scenario modeling (Phase 4).

Deterministic, fully transparent "what-if" projections. These are NOT
forecasts or predictions: every output is explicitly a hypothetical
projection built from user-chosen (or reference-suggested) annual growth
assumptions applied to the agency's real, validated latest-year figures.
No AI is involved in this module, and nothing here is presented as a
proven or likely outcome -- callers must always surface the assumptions
alongside the projection.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from kpi import add_kpis, cagr


@dataclass
class ScenarioAssumptions:
    ridership_growth_pct: float  # annual % change in UPT
    cost_growth_pct: float       # annual % change in OpExp Total
    fare_growth_pct: float       # annual % change in Fares
    years_ahead: int             # projection horizon in years


def suggest_reference_assumptions(agency_df: pd.DataFrame, lookback_years: int = 5) -> ScenarioAssumptions:
    """Suggests a starting point for the assumption sliders, computed as the
    agency's own trailing CAGR over `lookback_years` of real history. This is
    a reference point only -- the UI must let the user override every value,
    and the projection that follows is still a hypothetical, not a forecast."""
    df = agency_df.sort_values("year")
    if df.empty:
        return ScenarioAssumptions(0.0, 0.0, 0.0, 5)
    last_year = int(df["year"].max())
    first_year = max(int(df["year"].min()), last_year - lookback_years)
    lo = df[df["year"] == first_year]
    hi = df[df["year"] == last_year]
    n = last_year - first_year
    if lo.empty or hi.empty or n <= 0:
        return ScenarioAssumptions(0.0, 0.0, 0.0, 5)
    lo, hi = lo.iloc[0], hi.iloc[0]
    ridership = cagr(lo["UPT"], hi["UPT"], n) or 0.0
    cost = cagr(lo["OpExp Total"], hi["OpExp Total"], n) or 0.0
    fares = cagr(lo["Fares"], hi["Fares"], n) or 0.0
    return ScenarioAssumptions(
        ridership_growth_pct=round(ridership, 1),
        cost_growth_pct=round(cost, 1),
        fare_growth_pct=round(fares, 1),
        years_ahead=5,
    )


def project_scenario(agency_df: pd.DataFrame, assumptions: ScenarioAssumptions) -> pd.DataFrame:
    """Projects UPT, OpExp Total, and Fares forward from the agency's real
    latest validated year under constant-rate growth assumptions, then
    recomputes dependent KPIs. The first row of the result is the real,
    unmodified latest-year figure; every later row is a hypothetical
    projection flagged via the `is_projection` column."""
    df = agency_df.sort_values("year")
    if df.empty:
        raise ValueError("No historical data available to anchor a scenario to.")
    base = df.iloc[-1].copy()
    base_year = int(base["year"])

    rows = [{
        "year": base_year,
        "OpExp Total": base["OpExp Total"],
        "UPT": base["UPT"],
        "Fares": base["Fares"],
        "VRM": base.get("VRM"),
        "VRH": base.get("VRH"),
        "PMT": base.get("PMT"),
        "is_projection": False,
    }]
    for i in range(1, assumptions.years_ahead + 1):
        prev = rows[-1]
        rows.append({
            "year": base_year + i,
            "OpExp Total": prev["OpExp Total"] * (1 + assumptions.cost_growth_pct / 100),
            "UPT": prev["UPT"] * (1 + assumptions.ridership_growth_pct / 100),
            "Fares": prev["Fares"] * (1 + assumptions.fare_growth_pct / 100),
            "VRM": prev["VRM"],  # held constant: no assumption provided for service levels
            "VRH": prev["VRH"],
            "PMT": prev["PMT"],
            "is_projection": True,
        })
    out = pd.DataFrame(rows)
    return add_kpis(out)


def summarize_scenario(projection: pd.DataFrame) -> dict:
    """Headline deltas between the real anchor year and the final projected
    year, for a one-line summary. Always paired with the full assumptions
    and projection table in the UI -- never shown standalone."""
    base = projection.iloc[0]
    final = projection.iloc[-1]
    return {
        "base_year": int(base["year"]),
        "final_year": int(final["year"]),
        "opex_change_pct": (final["OpExp Total"] / base["OpExp Total"] - 1) * 100,
        "ridership_change_pct": (final["UPT"] / base["UPT"] - 1) * 100,
        "cost_per_trip_base": base["cost_per_trip"],
        "cost_per_trip_final": final["cost_per_trip"],
        "farebox_recovery_base": base["farebox_recovery"],
        "farebox_recovery_final": final["farebox_recovery"],
    }
