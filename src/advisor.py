"""Deterministic Strategic Consulting Advisor (Phase 4).

This module replaces any external AI/LLM integration. It is a fully
rule-based engine that turns the real historical diagnostic findings
(diagnostics.py) and a user-configured hypothetical financial scenario
(scenarios.py) into structured, evidence-based strategic recommendations.

No network calls, no API keys, no external services. Everything here runs
from data already loaded into memory, so it works identically with or
without internet access once the app's own data file and Python
dependencies are installed.

Every recommendation explicitly separates:
  - the business problem and supporting data (drawn straight from real
    diagnostic findings),
  - potential strategic actions (a fixed playbook keyed to the finding's
    rule type),
  - expected financial implications (always phrased as hypothetical, tied
    to the scenario the caller supplies -- never a promise or prediction),
  - implementation risks, and
  - what additional information would be needed before treating any of
    this as a real decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from diagnostics import Finding
from scenarios import ScenarioAssumptions

# Each entry: rule name (must match Finding.rule from diagnostics.py) -> playbook.
RULE_PLAYBOOK: dict[str, dict] = {
    "Cost growth vs. ridership growth": {
        "owner_role": "CFO / Finance & Budget",
        "target_kpi": "Cost per passenger trip ($)",
        "actions": [
            "Commission a function-level cost driver audit (labor, fuel, purchased transportation, contracts).",
            "Benchmark cost per vehicle revenue hour against structurally similar peer agencies.",
            "Review service-hour allocation against current ridership demand by route and time of day.",
        ],
        "risks": [
            "Cost-containment actions can affect service quality, headways, or existing labor agreements if not carefully scoped.",
            "Figures are nominal (not inflation-adjusted); part of the apparent gap may reflect general price inflation rather than agency-specific cost growth.",
        ],
        "info_needed": [
            "Function-level (labor/fuel/contract) cost breakdowns by year.",
            "Route- and time-of-day-level ridership and service-hour data.",
            "Local wage and fuel price indices, to separate inflation from real cost growth.",
        ],
    },
    "Cost-per-trip increase": {
        "owner_role": "CFO / Finance & Budget",
        "target_kpi": "Cost per passenger trip ($)",
        "actions": [
            "Decompose the cost-per-trip increase into its cost and ridership components to identify the larger driver.",
            "Evaluate targeted service adjustments on the lowest-productivity routes/time-of-day blocks.",
            "Compare cost-per-trip trajectory against a nominal cost-of-living/CPI benchmark before concluding it is agency-specific.",
        ],
        "risks": [
            "Service adjustments made without route-level data risk cutting service riders actually depend on.",
            "A nominal cost-per-trip increase can overstate the real (inflation-adjusted) cost pressure.",
        ],
        "info_needed": [
            "Inflation/CPI benchmark for the relevant metro area.",
            "Route-level ridership and cost allocation data.",
        ],
    },
    "Declining service productivity": {
        "owner_role": "COO / Service Planning",
        "target_kpi": "Passenger trips per vehicle revenue hour",
        "actions": [
            "Review schedules for low-ridership routes or time blocks as candidates for frequency or span adjustments.",
            "Evaluate vehicle-size right-sizing where ridership no longer matches originally planned capacity.",
            "Pilot demand-responsive or microtransit service in low-density areas currently served by fixed-route service.",
        ],
        "risks": [
            "Service reductions can disproportionately affect transit-dependent riders and raise equity concerns.",
            "Productivity changes may reflect demand shifts (e.g. remote work) rather than controllable service design.",
        ],
        "info_needed": [
            "Route- and stop-level ridership and boarding/alighting data.",
            "Equity/Title VI analysis of any proposed service changes.",
        ],
    },
    "Farebox recovery change": {
        "owner_role": "VP Revenue / Fare Policy",
        "target_kpi": "Farebox recovery ratio (%)",
        "actions": [
            "Review current fare policy, including any reduced- or free-fare programs, against the farebox recovery trend.",
            "Assess fare evasion and enforcement data, if available, as a contributor to the gap.",
            "Model fare-adjustment scenarios against estimated ridership elasticity before any fare change.",
        ],
        "risks": [
            "Fare increases can reduce ridership (price elasticity), partially offsetting the intended revenue gain.",
            "Fare policy changes have equity implications for low-income riders and often require public process.",
        ],
        "info_needed": [
            "Fare-policy history and any free/reduced-fare program enrollment data.",
            "Fare evasion estimates, where collected.",
            "Ridership price-elasticity estimates for this market.",
        ],
    },
}

DEFAULT_PLAYBOOK = {
    "owner_role": "Data & Performance Management",
    "target_kpi": "Monitor at next quarterly review",
    "actions": ["Continue monitoring this trend; no specific action is indicated by current thresholds."],
    "risks": ["None identified at this time."],
    "info_needed": ["Continued quarterly tracking to confirm whether the trend persists."],
}


@dataclass
class Recommendation:
    title: str
    priority: str  # "high", "medium", "low"
    business_problem: str
    supporting_data: list[str]
    strategic_actions: list[str]
    financial_implications: str
    risks: list[str]
    additional_info_needed: list[str]
    owner_role: str
    target_kpi: str
    source_rule: str = field(default="")


def _financial_implications_text(
    agency: str, assumptions: ScenarioAssumptions | None, scenario_summary: dict | None
) -> str:
    if not scenario_summary or not assumptions:
        return (
            "No financial scenario has been configured. Visit the Strategic Scenarios tab to model "
            "a hypothetical projection before estimating financial implications."
        )
    # Plain "$" here -- this text is reused as-is in the PowerPoint export
    # (report_generator.py), which needs literal dollar signs. Callers that
    # render it through Streamlit markdown (app.py) must escape "$" for
    # display themselves, since Streamlit's markdown treats "$...$" as LaTeX.
    return (
        f"Hypothetical only -- not a forecast. Under the scenario modeled for {agency} "
        f"(ridership {assumptions.ridership_growth_pct:+.1f}%/yr, cost {assumptions.cost_growth_pct:+.1f}%/yr, "
        f"fares {assumptions.fare_growth_pct:+.1f}%/yr, held constant for {assumptions.years_ahead} years), "
        f"cost per trip would move from ${scenario_summary['cost_per_trip_base']:.2f} "
        f"({scenario_summary['base_year']}, real) to ${scenario_summary['cost_per_trip_final']:.2f} "
        f"({scenario_summary['final_year']}, hypothetical projection) if current trends continued "
        "unchanged and no corrective action were taken."
    )


def generate_recommendations(
    agency: str,
    findings: list[Finding],
    assumptions: ScenarioAssumptions | None = None,
    scenario_summary: dict | None = None,
    max_recommendations: int = 4,
) -> list[Recommendation]:
    """Builds structured strategic recommendations for one agency from its
    real diagnostic findings and (optionally) a hypothetical scenario.
    Deterministic: the same inputs always produce the same output, with no
    network call or external model involved.
    """
    agency_findings = [f for f in findings if f.agency == agency]
    severity_order = {"high": 0, "medium": 1, "low": 2}
    agency_findings.sort(key=lambda f: severity_order.get(f.severity, 3))

    seen_rules: set[str] = set()
    recommendations: list[Recommendation] = []
    for f in agency_findings:
        if f.rule not in RULE_PLAYBOOK or f.rule in seen_rules:
            continue
        seen_rules.add(f.rule)
        playbook = RULE_PLAYBOOK[f.rule]
        recommendations.append(Recommendation(
            title=f.title.split(": ", 1)[-1].capitalize(),
            priority=f.severity,
            business_problem=f.implication,
            supporting_data=list(f.evidence),
            strategic_actions=list(playbook["actions"]),
            financial_implications=_financial_implications_text(agency, assumptions, scenario_summary),
            risks=list(playbook["risks"]),
            additional_info_needed=list(playbook["info_needed"]),
            owner_role=playbook["owner_role"],
            target_kpi=playbook["target_kpi"],
            source_rule=f.rule,
        ))
        if len(recommendations) >= max_recommendations:
            break

    if not recommendations:
        recommendations.append(Recommendation(
            title=f"{agency}: no material performance flags identified",
            priority="low",
            business_problem=(
                "No significant cost, productivity, or farebox-recovery gaps were identified for "
                "the selected period under current diagnostic thresholds."
            ),
            supporting_data=["See the Consulting Diagnostic Engine tab for the full historical trend."],
            strategic_actions=list(DEFAULT_PLAYBOOK["actions"]),
            financial_implications=_financial_implications_text(agency, assumptions, scenario_summary),
            risks=list(DEFAULT_PLAYBOOK["risks"]),
            additional_info_needed=list(DEFAULT_PLAYBOOK["info_needed"]),
            owner_role=DEFAULT_PLAYBOOK["owner_role"],
            target_kpi=DEFAULT_PLAYBOOK["target_kpi"],
        ))
    return recommendations


def build_90_day_roadmap(recommendations: list[Recommendation]) -> list[dict]:
    """Turns the top recommendations into a workstream-owner-milestone-KPI
    roadmap table for the 90-day action plan. Purely structural -- derives
    no new figures, just organizes the recommendations already produced."""
    roadmap = []
    for rec in recommendations:
        roadmap.append({
            "workstream": rec.title,
            "owner_role": rec.owner_role,
            "day_30_milestone": f"Validate: {rec.strategic_actions[0] if rec.strategic_actions else 'scope the issue'}",
            "day_60_milestone": (
                f"Analyze: {rec.strategic_actions[1]}" if len(rec.strategic_actions) > 1
                else "Complete supporting analysis"
            ),
            "day_90_milestone": (
                f"Decide: {rec.strategic_actions[2]}" if len(rec.strategic_actions) > 2
                else "Present findings and options to leadership"
            ),
            "target_kpi": rec.target_kpi,
        })
    return roadmap
