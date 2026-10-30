"""Rule-based consulting diagnostic engine.

Every finding is built strictly from values already computed in src/kpi.py
from the real NTD data. The engine never asserts a root cause: each finding
separates the observed evidence (fact, drawn from the data) from the
business implication (a reasoned but hedged interpretation) and an explicit
hypothesis that would require further investigation to confirm.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from kpi import cagr


@dataclass
class Finding:
    rule: str
    severity: str  # "high", "medium", "low"
    agency: str
    title: str
    evidence: list[str]
    implication: str
    hypothesis: str
    period: str
    detail_table: pd.DataFrame = field(default_factory=pd.DataFrame)


def _fmt_money(x: float) -> str:
    # Plain "$" here -- this text is reused as-is in the PowerPoint export,
    # which needs literal dollar signs. Callers that render it through
    # Streamlit markdown must escape "$" for display themselves, since
    # Streamlit's markdown treats "$...$" as LaTeX.
    return f"${x:,.0f}" if pd.notna(x) else "n/a"


def _fmt_pct(x: float) -> str:
    return f"{x:,.1f}%" if pd.notna(x) else "n/a"


def _endpoints(df: pd.DataFrame, year_lo: int, year_hi: int):
    row_lo = df[df["year"] == year_lo]
    row_hi = df[df["year"] == year_hi]
    if row_lo.empty or row_hi.empty:
        return None, None
    return row_lo.iloc[0], row_hi.iloc[0]


def rule_cost_outpacing_ridership(agency_df: pd.DataFrame, agency: str, year_lo: int, year_hi: int) -> Finding | None:
    lo, hi = _endpoints(agency_df, year_lo, year_hi)
    if lo is None:
        return None
    n = year_hi - year_lo
    cost_cagr = cagr(lo["OpExp Total"], hi["OpExp Total"], n)
    ridership_cagr = cagr(lo["UPT"], hi["UPT"], n)
    if cost_cagr is None or ridership_cagr is None:
        return None
    gap = cost_cagr - ridership_cagr
    if gap <= 1.0:
        return None
    severity = "high" if gap > 5 else "medium"
    return Finding(
        rule="Cost growth vs. ridership growth",
        severity=severity,
        agency=agency,
        title=f"{agency}: operating costs grew faster than ridership, {year_lo}–{year_hi}",
        evidence=[
            f"Total operating expense CAGR: {_fmt_pct(cost_cagr)}/yr "
            f"({_fmt_money(lo['OpExp Total'])} -> {_fmt_money(hi['OpExp Total'])}).",
            f"Unlinked passenger trips CAGR: {_fmt_pct(ridership_cagr)}/yr "
            f"({lo['UPT']:,.0f} -> {hi['UPT']:,.0f} trips).",
            f"Growth gap (cost CAGR minus ridership CAGR): {_fmt_pct(gap)} percentage points/yr.",
        ],
        implication=(
            "If this gap persists, cost per trip will keep rising even without any change in "
            "service quality, which pressures farebox recovery and the subsidy burden per rider."
        ),
        hypothesis=(
            "Hypothesis requiring further investigation: the gap could reflect inflation in "
            "labor/fuel/contract costs, service expansion that has not yet attracted riders, "
            "post-pandemic ridership recovery lagging restored service levels, or a combination. "
            "This is not confirmed by this dataset alone -- it would need cost-driver detail "
            "(e.g. wage/fuel indices, service-hours vs. ridership by route) to isolate the cause."
        ),
        period=f"{year_lo}–{year_hi}",
    )


def rule_declining_productivity(agency_df: pd.DataFrame, agency: str, year_lo: int, year_hi: int) -> Finding | None:
    lo, hi = _endpoints(agency_df, year_lo, year_hi)
    if lo is None:
        return None
    n = year_hi - year_lo
    prod_cagr = cagr(lo["trips_per_vrh"], hi["trips_per_vrh"], n)
    if prod_cagr is None or prod_cagr >= -1.0:
        return None
    severity = "high" if prod_cagr < -5 else "medium"
    return Finding(
        rule="Declining service productivity",
        severity=severity,
        agency=agency,
        title=f"{agency}: passengers carried per vehicle revenue hour declined, {year_lo}–{year_hi}",
        evidence=[
            f"Trips per vehicle revenue hour: {lo['trips_per_vrh']:.2f} -> {hi['trips_per_vrh']:.2f} "
            f"({_fmt_pct(prod_cagr)}/yr CAGR).",
            f"Vehicle revenue hours: {lo['VRH']:,.0f} -> {hi['VRH']:,.0f}.",
            f"Unlinked passenger trips: {lo['UPT']:,.0f} -> {hi['UPT']:,.0f}.",
        ],
        implication=(
            "Fewer riders are being served per hour of service operated, which raises the "
            "effective cost of carrying each passenger even if total service levels are stable."
        ),
        hypothesis=(
            "Hypothesis requiring further investigation: possible drivers include demand shifts "
            "(e.g. remote work, demographic change), service running in lower-demand areas or "
            "times, or schedule padding/slower operating speeds. Confirming the cause would "
            "require route- or time-of-day-level ridership and schedule data not present in "
            "this workbook."
        ),
        period=f"{year_lo}–{year_hi}",
    )


def rule_farebox_recovery_change(agency_df: pd.DataFrame, agency: str, year_lo: int, year_hi: int) -> Finding | None:
    lo, hi = _endpoints(agency_df, year_lo, year_hi)
    if lo is None or pd.isna(lo["farebox_recovery"]) or pd.isna(hi["farebox_recovery"]):
        return None
    delta_pp = (hi["farebox_recovery"] - lo["farebox_recovery"]) * 100
    if abs(delta_pp) <= 2.0:
        return None
    direction = "declined" if delta_pp < 0 else "improved"
    severity = "high" if abs(delta_pp) > 10 else "medium"
    return Finding(
        rule="Farebox recovery change",
        severity=severity,
        agency=agency,
        title=f"{agency}: farebox recovery ratio {direction} by {abs(delta_pp):.1f} points, {year_lo}–{year_hi}",
        evidence=[
            f"Farebox recovery (fares / total operating expense): "
            f"{lo['farebox_recovery']*100:.1f}% -> {hi['farebox_recovery']*100:.1f}%.",
            f"Fare revenue: {_fmt_money(lo['Fares'])} -> {_fmt_money(hi['Fares'])}.",
            f"Total operating expense: {_fmt_money(lo['OpExp Total'])} -> {_fmt_money(hi['OpExp Total'])}.",
        ],
        implication=(
            "A lower farebox recovery ratio means a larger share of operating costs must be "
            "covered by subsidy (taxes, grants, other non-fare revenue) per dollar spent."
            if delta_pp < 0 else
            "A higher farebox recovery ratio reduces reliance on subsidy per dollar of operating "
            "cost, all else equal."
        ),
        hypothesis=(
            "Hypothesis requiring further investigation: changes in fare policy, ridership mix, "
            "fare evasion, or free/reduced-fare programs could all contribute; the NTD service "
            "data alone cannot distinguish between these without fare-policy records."
        ),
        period=f"{year_lo}–{year_hi}",
    )


def rule_cost_per_trip_increase(agency_df: pd.DataFrame, agency: str, year_lo: int, year_hi: int) -> Finding | None:
    lo, hi = _endpoints(agency_df, year_lo, year_hi)
    if lo is None or pd.isna(lo["cost_per_trip"]) or pd.isna(hi["cost_per_trip"]) or lo["cost_per_trip"] <= 0:
        return None
    pct_change = (hi["cost_per_trip"] / lo["cost_per_trip"] - 1) * 100
    if pct_change <= 15.0:
        return None
    severity = "high" if pct_change > 40 else "medium"
    return Finding(
        rule="Cost-per-trip increase",
        severity=severity,
        agency=agency,
        title=f"{agency}: operating cost per passenger trip rose {pct_change:.0f}%, {year_lo}–{year_hi}",
        evidence=[
            f"Cost per unlinked passenger trip: {_fmt_money(lo['cost_per_trip'])} -> {_fmt_money(hi['cost_per_trip'])} "
            f"(nominal dollars, not inflation-adjusted).",
            f"Total operating expense: {_fmt_money(lo['OpExp Total'])} -> {_fmt_money(hi['OpExp Total'])}.",
            f"Unlinked passenger trips: {lo['UPT']:,.0f} -> {hi['UPT']:,.0f}.",
        ],
        implication=(
            "A rising nominal cost per trip increases the per-rider subsidy needed to sustain "
            "service at current fare levels, though part of the increase may simply reflect "
            "general inflation rather than agency-specific cost growth."
        ),
        hypothesis=(
            "Hypothesis requiring further investigation: disentangling inflation, service-level "
            "changes, and ridership recovery would require a cost index and route-level service "
            "data beyond this workbook's scope."
        ),
        period=f"{year_lo}–{year_hi}",
    )


def rule_unusual_yoy_swing(agency_df: pd.DataFrame, agency: str, year_lo: int, year_hi: int) -> list[Finding]:
    """Flags any year within the selected range whose YoY % change in a core
    metric is a statistical outlier relative to that agency's own YoY history
    for the metric (|z-score| > 1.5), using only years inside [year_lo, year_hi]."""
    findings: list[Finding] = []
    window = agency_df[(agency_df["year"] >= year_lo) & (agency_df["year"] <= year_hi)].sort_values("year")
    for metric, label in [("UPT", "unlinked passenger trips"), ("OpExp Total", "total operating expense")]:
        yoy = window[metric].pct_change() * 100
        if yoy.dropna().shape[0] < 3:
            continue
        mean, std = yoy.mean(), yoy.std()
        if not std or pd.isna(std) or std == 0:
            continue
        z = (yoy - mean) / std
        for idx in z[z.abs() > 1.5].index:
            yr = window.loc[idx, "year"]
            change = yoy.loc[idx]
            prior_yr = yr - 1
            findings.append(
                Finding(
                    rule="Unusual year-over-year swing",
                    severity="medium",
                    agency=agency,
                    title=f"{agency}: {label} moved {change:+.1f}% in {yr} vs. {prior_yr} -- statistically unusual for this series",
                    evidence=[
                        f"{label.capitalize()} YoY change in {yr}: {change:+.1f}%, vs. an average "
                        f"YoY change of {mean:+.1f}% (std dev {std:.1f} pts) over {year_lo}–{year_hi}.",
                    ],
                    implication=(
                        "A swing this far outside the agency's typical year-to-year variation "
                        "warrants a closer look before being treated as part of a steady trend."
                    ),
                    hypothesis=(
                        "Hypothesis requiring further investigation: large one-year swings in this "
                        "period often coincide with exogenous shocks (e.g. the COVID-19 pandemic and "
                        "subsequent recovery), service disruptions, or one-time reporting/accounting "
                        "changes. This dataset cannot confirm the cause on its own."
                    ),
                    period=f"{prior_yr}–{yr}",
                )
            )
    return findings


RULES = [
    rule_cost_outpacing_ridership,
    rule_declining_productivity,
    rule_farebox_recovery_change,
    rule_cost_per_trip_increase,
]


def run_diagnostics(kpi_df: pd.DataFrame, agencies: list[str], year_lo: int, year_hi: int) -> list[Finding]:
    """Runs every rule for every requested agency over [year_lo, year_hi]."""
    findings: list[Finding] = []
    for agency in agencies:
        agency_df = kpi_df[kpi_df["agency"] == agency].sort_values("year")
        if agency_df.empty or year_lo == year_hi:
            continue
        for rule_fn in RULES:
            result = rule_fn(agency_df, agency, year_lo, year_hi)
            if result is not None:
                findings.append(result)
        findings.extend(rule_unusual_yoy_swing(agency_df, agency, year_lo, year_hi))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 3), f.agency))
    return findings
