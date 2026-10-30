"""Tests for the Phase 4 financial scenario modeling module (src/scenarios.py).

These validate the deterministic math only -- no AI, no network calls.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kpi import agency_year_kpis  # noqa: E402
from scenarios import (  # noqa: E402
    ScenarioAssumptions,
    project_scenario,
    summarize_scenario,
    suggest_reference_assumptions,
)


@pytest.fixture(scope="module")
def la_metro_history():
    kpis = agency_year_kpis()
    return kpis[kpis["agency"] == "LA Metro"].sort_values("year")


def test_suggested_assumptions_are_finite_reference_values(la_metro_history):
    s = suggest_reference_assumptions(la_metro_history, lookback_years=5)
    assert isinstance(s.ridership_growth_pct, float)
    assert isinstance(s.cost_growth_pct, float)
    assert isinstance(s.fare_growth_pct, float)
    assert s.years_ahead == 5


def test_projection_first_row_matches_real_latest_year_exactly(la_metro_history):
    assumptions = ScenarioAssumptions(2.0, 3.0, 1.0, 5)
    proj = project_scenario(la_metro_history, assumptions)
    real_row = la_metro_history.iloc[-1]
    first = proj.iloc[0]
    assert bool(first["is_projection"]) is False
    assert first["year"] == real_row["year"]
    assert first["OpExp Total"] == pytest.approx(real_row["OpExp Total"])
    assert first["UPT"] == pytest.approx(real_row["UPT"])


def test_projection_has_correct_number_of_rows_and_years(la_metro_history):
    assumptions = ScenarioAssumptions(0.0, 0.0, 0.0, 7)
    proj = project_scenario(la_metro_history, assumptions)
    assert len(proj) == 8  # anchor year + 7 projected years
    base_year = la_metro_history["year"].max()
    assert proj["year"].tolist() == list(range(base_year, base_year + 8))


def test_zero_growth_assumptions_hold_values_flat(la_metro_history):
    assumptions = ScenarioAssumptions(0.0, 0.0, 0.0, 3)
    proj = project_scenario(la_metro_history, assumptions)
    assert proj["OpExp Total"].nunique() == 1
    assert proj["UPT"].nunique() == 1


def test_positive_growth_compounds_upward(la_metro_history):
    assumptions = ScenarioAssumptions(5.0, 5.0, 5.0, 3)
    proj = project_scenario(la_metro_history, assumptions)
    assert proj["OpExp Total"].is_monotonic_increasing
    assert proj["UPT"].is_monotonic_increasing


def test_all_projected_rows_are_flagged(la_metro_history):
    assumptions = ScenarioAssumptions(1.0, 1.0, 1.0, 4)
    proj = project_scenario(la_metro_history, assumptions)
    assert proj.iloc[1:]["is_projection"].all()
    assert not proj.iloc[0]["is_projection"]


def test_summary_matches_first_and_last_rows(la_metro_history):
    assumptions = ScenarioAssumptions(2.0, -1.0, 3.0, 5)
    proj = project_scenario(la_metro_history, assumptions)
    summary = summarize_scenario(proj)
    assert summary["base_year"] == int(proj.iloc[0]["year"])
    assert summary["final_year"] == int(proj.iloc[-1]["year"])
    expected_opex_change = (proj.iloc[-1]["OpExp Total"] / proj.iloc[0]["OpExp Total"] - 1) * 100
    assert summary["opex_change_pct"] == pytest.approx(expected_opex_change)


def test_empty_history_raises_instead_of_fabricating(la_metro_history):
    empty = la_metro_history.iloc[0:0]
    with pytest.raises(ValueError):
        project_scenario(empty, ScenarioAssumptions(1.0, 1.0, 1.0, 5))
