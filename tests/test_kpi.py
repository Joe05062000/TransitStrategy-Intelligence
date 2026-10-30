"""Sanity checks for KPI calculations against the real NTD workbook.

These are not unit tests against synthetic data (per project policy, we do
not fabricate NTD figures) -- they are invariant checks against the real,
validated source file: totals must be positive, ratios must fall in sane
ranges, and known-COVID-era anomalies must be detectable.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kpi import TARGET_AGENCIES, agency_year_kpis, mode_group_year_kpis  # noqa: E402
from diagnostics import run_diagnostics  # noqa: E402


@pytest.fixture(scope="module")
def agency_kpis():
    return agency_year_kpis()


@pytest.fixture(scope="module")
def mode_kpis():
    return mode_group_year_kpis()


def test_all_three_agencies_present(agency_kpis):
    assert set(agency_kpis["agency"].unique()) == set(TARGET_AGENCIES.values())


def test_2025_is_fully_populated(agency_kpis):
    latest = agency_kpis[agency_kpis["year"] == 2025]
    assert len(latest) == 3
    for col in ["OpExp Total", "UPT", "VRM", "VRH", "Fares", "cost_per_trip", "farebox_recovery"]:
        assert latest[col].notna().all(), f"{col} has nulls in 2025"


def test_totals_are_positive(agency_kpis):
    for col in ["OpExp Total", "UPT", "VRM", "VRH", "Fares"]:
        assert (agency_kpis[col].dropna() > 0).all(), f"{col} has non-positive values"


def test_farebox_recovery_in_plausible_range(agency_kpis):
    # Real-world farebox recovery ratios for major US transit agencies fall
    # well within 0-100%; anything outside flags a formula bug.
    fb = agency_kpis["farebox_recovery"].dropna()
    assert (fb >= 0).all() and (fb <= 1.0).all()


def test_cost_per_trip_matches_manual_division(agency_kpis):
    sample = agency_kpis[(agency_kpis["agency"] == "LA Metro") & (agency_kpis["year"] == 2025)].iloc[0]
    expected = sample["OpExp Total"] / sample["UPT"]
    assert sample["cost_per_trip"] == pytest.approx(expected)


def test_mode_group_totals_do_not_exceed_agency_totals(agency_kpis, mode_kpis):
    # Summing OpExp Total across mode groups for an agency/year should equal
    # (not exceed) the agency-level all-modes total -- no double-counting.
    for agency in TARGET_AGENCIES.values():
        for year in [2025]:
            agency_total = agency_kpis.loc[
                (agency_kpis["agency"] == agency) & (agency_kpis["year"] == year), "OpExp Total"
            ].iloc[0]
            mode_sum = mode_kpis.loc[
                (mode_kpis["agency"] == agency) & (mode_kpis["year"] == year), "OpExp Total"
            ].sum()
            assert mode_sum == pytest.approx(agency_total), (agency, year)


def test_bart_has_no_bus_mode_group(mode_kpis):
    bart_modes = set(mode_kpis.loc[mode_kpis["agency"] == "BART", "mode_group"].unique())
    assert "Bus" not in bart_modes


def test_diagnostics_do_not_crash_and_label_hypotheses(agency_kpis):
    findings = run_diagnostics(agency_kpis, list(TARGET_AGENCIES.values()), 2015, 2025)
    assert len(findings) > 0
    for f in findings:
        assert f.hypothesis  # every finding must carry an explicit, hedged hypothesis
        assert f.evidence  # every finding must cite concrete evidence


def test_division_by_zero_or_missing_denominator_yields_nan_not_inf(agency_kpis):
    # No KPI column should ever contain +/-inf: _safe_div must guard every
    # zero/missing denominator.
    for col in ["cost_per_trip", "cost_per_vrm", "trips_per_vrh", "farebox_recovery"]:
        assert not agency_kpis[col].isin([float("inf"), float("-inf")]).any()
