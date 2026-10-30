"""Tests for the deterministic Strategic Consulting Advisor (src/advisor.py).

No network calls, no AI/LLM -- these validate that recommendations are
derived consistently from real diagnostic findings and a scenario summary.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from advisor import Recommendation, build_90_day_roadmap, generate_recommendations  # noqa: E402
from diagnostics import run_diagnostics  # noqa: E402
from kpi import TARGET_AGENCIES, agency_year_kpis  # noqa: E402
from scenarios import project_scenario, summarize_scenario, suggest_reference_assumptions  # noqa: E402


@pytest.fixture(scope="module")
def la_metro_context():
    agency_kpis = agency_year_kpis()
    hist = agency_kpis[agency_kpis["agency"] == "LA Metro"].sort_values("year")
    assumptions = suggest_reference_assumptions(hist, lookback_years=5)
    projection = project_scenario(hist, assumptions)
    summary = summarize_scenario(projection)
    findings = run_diagnostics(agency_kpis, list(TARGET_AGENCIES.values()), 2015, 2025)
    return {"findings": findings, "assumptions": assumptions, "summary": summary}


def test_generate_recommendations_returns_recommendation_objects(la_metro_context):
    recs = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"], la_metro_context["summary"]
    )
    assert len(recs) > 0
    assert all(isinstance(r, Recommendation) for r in recs)


def test_recommendations_are_capped_and_deduplicated_by_rule(la_metro_context):
    recs = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"],
        la_metro_context["summary"], max_recommendations=2,
    )
    assert len(recs) <= 2
    rules = [r.source_rule for r in recs if r.source_rule]
    assert len(rules) == len(set(rules))  # no duplicate rule types


def test_each_recommendation_has_all_required_fields(la_metro_context):
    recs = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"], la_metro_context["summary"]
    )
    for r in recs:
        assert r.business_problem
        assert r.supporting_data  # real evidence, non-empty
        assert r.strategic_actions
        assert r.financial_implications
        assert "Hypothetical" in r.financial_implications or "hypothetical" in r.financial_implications.lower()
        assert r.risks
        assert r.additional_info_needed
        assert r.owner_role
        assert r.target_kpi
        assert r.priority in ("high", "medium", "low")


def test_financial_implications_cite_real_and_hypothetical_years(la_metro_context):
    recs = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"], la_metro_context["summary"]
    )
    summary = la_metro_context["summary"]
    for r in recs:
        assert str(summary["base_year"]) in r.financial_implications
        assert str(summary["final_year"]) in r.financial_implications


def test_no_findings_yields_a_safe_fallback_recommendation():
    recs = generate_recommendations("LA Metro", [], None, None)
    assert len(recs) == 1
    assert "no material" in recs[0].title.lower()
    assert "No financial scenario" in recs[0].financial_implications


def test_deterministic_same_inputs_same_outputs(la_metro_context):
    recs1 = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"], la_metro_context["summary"]
    )
    recs2 = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"], la_metro_context["summary"]
    )
    assert [r.title for r in recs1] == [r.title for r in recs2]
    assert [r.financial_implications for r in recs1] == [r.financial_implications for r in recs2]


def test_build_90_day_roadmap_has_one_row_per_recommendation(la_metro_context):
    recs = generate_recommendations(
        "LA Metro", la_metro_context["findings"], la_metro_context["assumptions"], la_metro_context["summary"]
    )
    roadmap = build_90_day_roadmap(recs)
    assert len(roadmap) == len(recs)
    for row in roadmap:
        assert set(row.keys()) == {
            "workstream", "owner_role", "day_30_milestone", "day_60_milestone", "day_90_milestone", "target_kpi",
        }
        assert all(row.values())


def test_advisor_module_imports_no_network_or_ai_dependency():
    import advisor
    src = Path(advisor.__file__).read_text()
    for forbidden in ("anthropic", "openai", "requests", "urllib", "httpx", "ai_advisor"):
        assert forbidden not in src.lower()
