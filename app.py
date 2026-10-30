"""TransitStrategy Intelligence - Management Consulting Performance Diagnostic.

Tagline: "Turning Transit Data into Strategic Decisions"

Independent portfolio project. Primary case study: LA Metro, benchmarked
against Sacramento Regional Transit and BART using real FTA National Transit
Database (NTD) TS2.1 data. See ARCHITECTURE.md for the module layout and
DEPLOYMENT.md for the Streamlit Community Cloud deployment checklist.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from advisor import build_90_day_roadmap, generate_recommendations  # noqa: E402
from diagnostics import run_diagnostics  # noqa: E402
from kpi import (  # noqa: E402
    MODE_LABELS,
    TARGET_AGENCIES,
    YEARS,
    add_yoy_changes,
    agency_year_kpis,
    mode_group_year_kpis,
)
from report_generator import build_report  # noqa: E402
from scenarios import ScenarioAssumptions, project_scenario, summarize_scenario, suggest_reference_assumptions  # noqa: E402

PRIMARY_AGENCY = "LA Metro"
COMPARISON_AGENCIES = ["Sacramento RT", "BART"]
ACCENT = "#0B5FFF"
AGENCY_COLORS = {"LA Metro": "#0B5FFF", "Sacramento RT": "#E08A00", "BART": "#1F9D55"}

st.set_page_config(page_title="TransitStrategy Intelligence", page_icon="\U0001F686", layout="wide")


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
try:
    agency_kpis = agency_year_kpis()
    mode_kpis = mode_group_year_kpis()
except FileNotFoundError as e:
    st.error(
        "Could not load the NTD source workbook from `data/raw/`. "
        f"Details: {e}"
    )
    st.stop()

agency_kpis = add_yoy_changes(
    agency_kpis, ["agency"], ["OpExp Total", "UPT", "VRM", "VRH", "cost_per_trip", "trips_per_vrh"]
)

# --------------------------------------------------------------------------
# Sidebar - global filters
# --------------------------------------------------------------------------
st.sidebar.title("\U0001F686 TransitStrategy Intelligence")
st.sidebar.caption("Turning Transit Data into Strategic Decisions")
st.sidebar.divider()

st.sidebar.markdown("**Primary client**")
st.sidebar.info(PRIMARY_AGENCY)

comparison_selected = st.sidebar.multiselect(
    "Peer agencies for comparison",
    options=COMPARISON_AGENCIES,
    default=COMPARISON_AGENCIES,
)
active_agencies = [PRIMARY_AGENCY] + comparison_selected

year_lo, year_hi = st.sidebar.select_slider(
    "Reporting years",
    options=YEARS,
    value=(2015, 2025),
)

st.sidebar.divider()
st.sidebar.caption(
    "Source: FTA National Transit Database, TS2.1 Service Data and Operating "
    "Expenses Time Series by Mode (2025 report year file). See the "
    "Methodology tab for formulas and caveats."
)

year_mask = (agency_kpis["year"] >= year_lo) & (agency_kpis["year"] <= year_hi)
mode_year_mask = (mode_kpis["year"] >= year_lo) & (mode_kpis["year"] <= year_hi)
view = agency_kpis[year_mask & agency_kpis["agency"].isin(active_agencies)].copy()
mode_view = mode_kpis[mode_year_mask & mode_kpis["agency"].isin(active_agencies)].copy()

if view.empty:
    st.warning("No data in the selected year range.")
    st.stop()


def fmt_money(x) -> str:
    return f"${x:,.0f}" if pd.notna(x) else "n/a"


def fmt_money2(x) -> str:
    return f"${x:,.2f}" if pd.notna(x) else "n/a"


def md_safe(text: str) -> str:
    """Escapes '$' before passing text to st.markdown/st.info, so Streamlit's
    markdown renderer doesn't mistake a dollar amount for LaTeX math."""
    return text.replace("$", "&#36;")


def fmt_int(x) -> str:
    return f"{x:,.0f}" if pd.notna(x) else "n/a"


def fmt_pct(x, digits=1) -> str:
    return f"{x:,.{digits}f}%" if pd.notna(x) else "n/a"


def kpi_delta(latest, prior):
    if pd.isna(latest) or pd.isna(prior) or prior == 0:
        return None
    return (latest / prior - 1) * 100


def line_chart(df, y_col, title, y_title, y_is_pct=False, y_is_money=False):
    fig = go.Figure()
    for agency in active_agencies:
        sub = df[df["agency"] == agency].sort_values("year")
        fig.add_trace(
            go.Scatter(
                x=sub["year"],
                y=sub[y_col],
                mode="lines+markers",
                name=agency,
                line=dict(color=AGENCY_COLORS.get(agency), width=3),
                marker=dict(size=6),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Report year",
        yaxis_title=y_title,
        template="plotly_white",
        legend_title="Agency",
        height=400,
        margin=dict(t=60, b=40),
    )
    if y_is_pct:
        fig.update_yaxes(tickformat=".0%")
    if y_is_money:
        fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


st.caption(
    "\U0001F4C1 Independent portfolio project — not affiliated with LA Metro, Sacramento RT, "
    "BART, or the FTA. No external AI/LLM API is used anywhere. Historical figures are real "
    "NTD data; scenario projections and strategic recommendations are hypothetical and "
    "clearly labeled wherever they appear."
)
st.title("Performance Diagnostic: " + PRIMARY_AGENCY)
st.markdown("*Turning Transit Data into Strategic Decisions*")
st.caption(
    f"Benchmarked against {', '.join(comparison_selected) if comparison_selected else 'no peer agencies (none selected)'} "
    f"· Report years {year_lo}–{year_hi} · Source: FTA National Transit Database (NTD)"
)

tab_home, tab_overview, tab_perf, tab_bench, tab_diag, tab_scenarios, tab_report, tab_advisor, tab_meta = st.tabs(
    [
        "Home",
        "1. Executive Overview",
        "2. Financial & Operational Performance",
        "3. Peer Benchmarking",
        "4. Consulting Diagnostic Engine",
        "5. Strategic Scenarios",
        "6. Executive Report",
        "7. Strategic Consulting Advisor",
        "8. Methodology & Data Notes",
    ]
)

# --------------------------------------------------------------------------
# TAB 0 - Home / landing page
# --------------------------------------------------------------------------
with tab_home:
    st.markdown("## Welcome to TransitStrategy Intelligence")
    st.markdown("##### *Turning Transit Data into Strategic Decisions*")
    st.markdown(
        """
        **TransitStrategy Intelligence** is a management-consulting performance diagnostic
        for U.S. rail and public transportation agencies, built entirely on real data from
        the Federal Transit Administration's **National Transit Database (NTD)**.

        > This is an **independent portfolio project**, built to demonstrate data analysis,
        > financial modeling, and application engineering. It is not affiliated with,
        > endorsed by, or representing LA Metro, Sacramento Regional Transit, BART, the
        > FTA, or any employer.
        """
    )

    st.markdown("### The consulting problem")
    st.markdown(
        """
        Transit agencies across the U.S. face a common challenge: operating costs have
        risen while ridership has not fully recovered from the pandemic-era decline, and
        farebox revenue covers a shrinking share of operating expense. Agency leadership
        needs a clear, evidence-based view of *where* performance is diverging from
        historical trends, *how* their agency compares to structurally similar peers, and
        *what* levers are available to close the gap — without over-claiming certainty
        about root causes that the data alone cannot prove.
        """
    )

    st.markdown("### Methodology")
    st.markdown(
        """
        1. **Data processing** (`src/ntd_loader.py`, `src/kpi.py`) — loads the real NTD
           TS2.1 workbook and computes standard transit KPIs (cost per trip, farebox
           recovery, service productivity, etc.) with no fabricated or interpolated values.
        2. **Historical diagnostics** (`src/diagnostics.py`) — a rule-based engine that
           flags significant trends in the real data, always separating observed evidence
           from an explicitly labeled, unconfirmed hypothesis.
        3. **Strategic scenarios** (`src/scenarios.py`) — a transparent, user-adjustable
           "what-if" projection tool. Every output is labeled a hypothetical projection,
           never a forecast.
        4. **Strategic Consulting Advisor** (`src/advisor.py`) — a deterministic, rule-based
           engine (no external AI/LLM, no API key, no internet access required) that turns
           the real findings and scenario outputs into structured recommendations: business
           problem, supporting data, strategic actions, hypothetical financial implications,
           risks, and what further information would be needed before treating any of it as
           a real decision.
        """
    )

    st.markdown("### Data source")
    st.markdown(
        """
        FTA National Transit Database (NTD), **TS2.1 — Service Data and Operating
        Expenses Time Series by Mode**, 2025 report year file, covering 2015–2025.
        Agencies covered in this demo: **LA Metro**, **Sacramento Regional Transit**, and
        **BART**. See the Methodology tab for exact KPI formulas and caveats, and
        `reports/phase2_data_quality_report.md` for the full source-data inspection.
        """
    )

    st.markdown("### Guided tour")
    st.info(
        "**Start here:** the sidebar defaults to LA Metro as the primary case study, "
        "benchmarked against both peer agencies across the full 2015–2025 history. Use "
        "**1. Executive Overview** for the headline KPIs, **4. Consulting Diagnostic "
        "Engine** for the real findings, **5. Strategic Scenarios** to try your own "
        "assumptions, **6. Executive Report** to download a PowerPoint deck, and "
        "**7. Strategic Consulting Advisor** for structured, evidence-based recommendations. "
        "No account, install, upload, or API key is required for any of this."
    )
    st.caption(
        "This application uses no external AI/LLM API anywhere — every chart, finding, "
        "scenario, recommendation, and report download is a deterministic calculation that "
        "works fully offline once the app's data file and dependencies are installed."
    )

# --------------------------------------------------------------------------
# TAB 1 - Executive Overview
# --------------------------------------------------------------------------
with tab_overview:
    primary = view[view["agency"] == PRIMARY_AGENCY].sort_values("year")
    if primary.empty:
        st.warning("No LA Metro data in the selected range.")
    else:
        latest = primary.iloc[-1]
        prior = primary.iloc[-2] if len(primary) > 1 else None

        st.markdown(f"#### {PRIMARY_AGENCY} — Executive KPIs, report year {int(latest['year'])}")
        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)

        def card(col, label, value, prior_value, help_text):
            delta = kpi_delta(prior_value[0], prior_value[1]) if prior_value else None
            col.metric(
                label,
                value,
                f"{delta:+.1f}% vs. {int(prior['year'])}" if (prior is not None and delta is not None) else None,
                help=help_text,
            )

        card(c1, "Total operating expense", fmt_money(latest["OpExp Total"]),
             (latest["OpExp Total"], prior["OpExp Total"]) if prior is not None else None,
             "Sum of operating expenses across all actively operated modes (OpExp Total).")
        card(c2, "Annual passenger trips (UPT)", fmt_int(latest["UPT"]),
             (latest["UPT"], prior["UPT"]) if prior is not None else None,
             "Unlinked passenger trips: each boarding counted once, summed across all operated modes.")
        card(c3, "Cost per passenger trip", fmt_money2(latest["cost_per_trip"]),
             (latest["cost_per_trip"], prior["cost_per_trip"]) if prior is not None else None,
             "Total operating expense / unlinked passenger trips.")
        card(c4, "Cost per vehicle revenue mile", fmt_money2(latest["cost_per_vrm"]),
             (latest["cost_per_vrm"], prior["cost_per_vrm"]) if prior is not None else None,
             "Total operating expense / vehicle revenue miles.")
        card(c5, "Trips per vehicle revenue hour", f"{latest['trips_per_vrh']:.2f}" if pd.notna(latest["trips_per_vrh"]) else "n/a",
             (latest["trips_per_vrh"], prior["trips_per_vrh"]) if prior is not None else None,
             "Unlinked passenger trips / vehicle revenue hours -- a core service-productivity measure.")
        card(c6, "Farebox recovery ratio", fmt_pct(latest["farebox_recovery"] * 100) if pd.notna(latest["farebox_recovery"]) else "n/a",
             (latest["farebox_recovery"], prior["farebox_recovery"]) if prior is not None else None,
             "Fare revenue / total operating expense -- share of operating cost covered by fares.")

        st.divider()
        st.markdown("#### Trends, " + f"{year_lo}–{year_hi}")
        metric_choice = st.radio(
            "Chart metric",
            [
                "Total operating expense", "Annual passenger trips", "Cost per passenger trip",
                "Cost per vehicle revenue mile", "Trips per vehicle revenue hour", "Farebox recovery ratio",
            ],
            horizontal=True,
        )
        metric_map = {
            "Total operating expense": ("OpExp Total", "Operating expense ($)", False, True),
            "Annual passenger trips": ("UPT", "Unlinked passenger trips", False, False),
            "Cost per passenger trip": ("cost_per_trip", "Cost per trip ($)", False, True),
            "Cost per vehicle revenue mile": ("cost_per_vrm", "Cost per VRM ($)", False, True),
            "Trips per vehicle revenue hour": ("trips_per_vrh", "Trips per VRH", False, False),
            "Farebox recovery ratio": ("farebox_recovery", "Farebox recovery", True, False),
        }
        col, title, is_pct, is_money = metric_map[metric_choice]
        st.plotly_chart(
            line_chart(view, col, f"{metric_choice}, {year_lo}–{year_hi}", title, is_pct, is_money),
            use_container_width=True,
        )
        st.caption(
            "All agencies shown combine every actively operated mode (rail, bus, demand "
            "response, etc.) into a single agency-level total. Because agencies differ "
            "substantially in mode mix, use the Peer Benchmarking tab for like-for-like "
            "mode comparisons rather than comparing these all-modes totals directly."
        )

# --------------------------------------------------------------------------
# TAB 2 - Financial & Operational Performance
# --------------------------------------------------------------------------
with tab_perf:
    st.markdown("#### Growth index: operating expense vs. ridership (2015 = 100)")
    st.caption(
        "Indexing both series to the first year in the selected range isolates relative "
        "growth rates regardless of each agency's absolute scale."
    )
    fig = go.Figure()
    for agency in active_agencies:
        sub = view[view["agency"] == agency].sort_values("year")
        if sub.empty:
            continue
        base_cost = sub["OpExp Total"].iloc[0]
        base_upt = sub["UPT"].iloc[0]
        if pd.isna(base_cost) or base_cost == 0 or pd.isna(base_upt) or base_upt == 0:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["OpExp Total"] / base_cost * 100,
            mode="lines+markers", name=f"{agency} — Opex index",
            line=dict(color=AGENCY_COLORS.get(agency), width=3),
        ))
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["UPT"] / base_upt * 100,
            mode="lines+markers", name=f"{agency} — Ridership index",
            line=dict(color=AGENCY_COLORS.get(agency), width=2, dash="dot"),
        ))
    fig.update_layout(
        template="plotly_white", height=450, xaxis_title="Report year",
        yaxis_title=f"Index ({year_lo} = 100)", legend_title=None,
        margin=dict(t=30, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Service productivity trend")
        st.plotly_chart(
            line_chart(view, "trips_per_vrh", "Passenger trips per vehicle revenue hour",
                       "Trips per VRH"),
            use_container_width=True,
        )
    with col_b:
        st.markdown("#### Cost per passenger trip trend")
        st.plotly_chart(
            line_chart(view, "cost_per_trip", "Operating cost per passenger trip",
                       "Cost per trip ($)", y_is_money=True),
            use_container_width=True,
        )

    st.divider()
    st.markdown("#### Year-over-year change")
    yoy_metric = st.selectbox(
        "Metric",
        ["OpExp Total", "UPT", "VRM", "VRH", "cost_per_trip", "trips_per_vrh"],
        format_func=lambda c: {
            "OpExp Total": "Total operating expense", "UPT": "Passenger trips",
            "VRM": "Vehicle revenue miles", "VRH": "Vehicle revenue hours",
            "cost_per_trip": "Cost per trip", "trips_per_vrh": "Trips per VRH",
        }[c],
    )
    yoy_col = f"{yoy_metric}_yoy_pct"
    fig2 = go.Figure()
    for agency in active_agencies:
        sub = view[view["agency"] == agency].sort_values("year")
        fig2.add_trace(go.Bar(x=sub["year"], y=sub[yoy_col], name=agency,
                               marker_color=AGENCY_COLORS.get(agency)))
    fig2.update_layout(
        template="plotly_white", barmode="group", height=400,
        xaxis_title="Report year", yaxis_title="YoY change (%)",
        margin=dict(t=30, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True)

    biggest_gap = (
        view.dropna(subset=[yoy_col])
        .assign(abs_change=lambda d: d[yoy_col].abs())
        .sort_values("abs_change", ascending=False)
        .head(5)
    )
    if not biggest_gap.empty:
        st.markdown("**Largest single-year moves in the selected range**")
        st.dataframe(
            biggest_gap[["agency", "year", yoy_col]].rename(
                columns={"agency": "Agency", "year": "Year", yoy_col: "YoY change (%)"}
            ).style.format({"YoY change (%)": "{:+.1f}"}),
            hide_index=True, use_container_width=True,
        )

# --------------------------------------------------------------------------
# TAB 3 - Peer Benchmarking
# --------------------------------------------------------------------------
with tab_bench:
    st.markdown("#### Benchmark by mode group")
    st.warning(
        "**Benchmarking note:** BART operates no bus service, and Sacramento RT and LA Metro "
        "each mix rail, bus, and demand-response service in different proportions. Comparing "
        "all-modes totals directly would conflate differences in mode mix with differences in "
        "performance. Select a single mode group below so each agency is compared only against "
        "its peers' service of the *same type* (rail-to-rail, bus-to-bus, etc.)."
    )

    available_groups = sorted(mode_view.loc[mode_view["agency"].isin(active_agencies), "mode_group"].unique())
    preferred_order = [g for g in ["Rail", "Bus", "Demand Response", "Ferry", "Other"] if g in available_groups]
    mode_group_choice = st.selectbox("Mode group", preferred_order or available_groups)

    bench = mode_view[mode_view["mode_group"] == mode_group_choice].copy()
    agencies_with_mode = sorted(bench.loc[bench["UPT"].notna() | bench["OpExp Total"].notna(), "agency"].unique())
    missing = [a for a in active_agencies if a not in agencies_with_mode]
    if missing:
        st.caption(f"No {mode_group_choice} service reported for: {', '.join(missing)} (excluded below).")
    bench = bench[bench["agency"].isin(agencies_with_mode)]

    if bench.empty:
        st.info(f"No {mode_group_choice} data available for the selected agencies/years.")
    else:
        bench_metric = st.selectbox(
            "KPI to compare",
            ["cost_per_trip", "cost_per_vrm", "trips_per_vrh", "farebox_recovery", "OpExp Total", "UPT"],
            format_func=lambda c: {
                "cost_per_trip": "Cost per passenger trip", "cost_per_vrm": "Cost per vehicle revenue mile",
                "trips_per_vrh": "Trips per vehicle revenue hour", "farebox_recovery": "Farebox recovery ratio",
                "OpExp Total": "Total operating expense", "UPT": "Annual passenger trips",
            }[c],
        )
        is_pct = bench_metric == "farebox_recovery"
        is_money = bench_metric in ("cost_per_trip", "cost_per_vrm", "OpExp Total")
        st.plotly_chart(
            line_chart(
                bench.rename(columns={"agency": "agency"}), bench_metric,
                f"{mode_group_choice}: {bench_metric.replace('_', ' ')}, {year_lo}–{year_hi}",
                bench_metric.replace("_", " "), is_pct, is_money,
            ),
            use_container_width=True,
        )

        latest_year_bench = bench[bench["year"] == bench["year"].max()]
        st.markdown(f"**Snapshot, report year {int(bench['year'].max())}**")
        display_cols = ["agency", "OpExp Total", "UPT", "VRM", "VRH", "cost_per_trip", "cost_per_vrm", "trips_per_vrh", "farebox_recovery"]
        snap = latest_year_bench[display_cols].rename(columns={
            "agency": "Agency", "OpExp Total": "Opex ($)", "UPT": "Trips",
            "VRM": "Veh. rev. miles", "VRH": "Veh. rev. hours",
            "cost_per_trip": "Cost/trip ($)", "cost_per_vrm": "Cost/VRM ($)",
            "trips_per_vrh": "Trips/VRH", "farebox_recovery": "Farebox recovery",
        })
        st.dataframe(
            snap.style.format({
                "Opex ($)": "${:,.0f}", "Trips": "{:,.0f}", "Veh. rev. miles": "{:,.0f}",
                "Veh. rev. hours": "{:,.0f}", "Cost/trip ($)": "${:,.2f}", "Cost/VRM ($)": "${:,.2f}",
                "Trips/VRH": "{:,.2f}", "Farebox recovery": "{:.1%}",
            }),
            hide_index=True, use_container_width=True,
        )

        with st.expander("Operating-environment context for this mode group"):
            st.markdown(
                """
                - **BART (Heavy Rail)** operates a long-haul, regional rapid-transit system
                  connecting multiple counties, with wide station spacing and high average trip
                  lengths relative to a typical light-rail or bus system.
                - **LA Metro (Heavy Rail / Light Rail)** operates a growing, more urban
                  rail network with closer station spacing in several corridors.
                - **Sacramento RT (Light Rail)** operates a smaller-scale light-rail network
                  serving a single, less dense urbanized area than LA or the Bay Area.
                - **Bus networks** differ in service area size, route density, and the share of
                  express/limited-stop vs. local service, all of which affect cost per mile and
                  passengers per hour independent of operational efficiency.

                These structural differences mean a KPI gap between agencies is informative but
                not, by itself, proof of better or worse management -- it is a starting point
                for the hypotheses raised in the Consulting Diagnostic Engine tab.
                """
            )

# --------------------------------------------------------------------------
# TAB 4 - Consulting Diagnostic Engine
# --------------------------------------------------------------------------
with tab_diag:
    st.markdown("#### Automated findings, " + f"{year_lo}–{year_hi}")
    st.caption(
        "Rule-based engine applied to agency-level KPIs (all operated modes combined). "
        "Every finding below is derived directly from the NTD figures shown as evidence; "
        "hypotheses are explicitly labeled as unconfirmed and would require further "
        "investigation beyond this dataset."
    )

    findings = run_diagnostics(agency_kpis, active_agencies, year_lo, year_hi)

    if not findings:
        st.success(
            "No material performance flags were identified for the selected agencies and "
            "year range under the current thresholds."
        )
    else:
        severity_badge = {"high": "\U0001F534 High", "medium": "\U0001F7E1 Medium", "low": "\U0001F7E2 Low"}
        severity_filter = st.multiselect(
            "Filter by severity", ["high", "medium", "low"], default=["high", "medium", "low"],
            format_func=lambda s: severity_badge[s],
        )
        shown = [f for f in findings if f.severity in severity_filter]
        st.caption(f"{len(shown)} of {len(findings)} findings shown.")

        for f in shown:
            with st.expander(f"{severity_badge[f.severity]} — {f.title}"):
                st.markdown(f"**Rule:** {f.rule}  \n**Agency:** {f.agency}  \n**Period:** {f.period}")
                st.markdown("**Evidence (from source data):**")
                for e in f.evidence:
                    st.markdown(f"- {md_safe(e)}")
                st.markdown(f"**Business implication:** {f.implication}")
                st.info(f"**Hypothesis (not confirmed by this data alone):** {f.hypothesis}")

# --------------------------------------------------------------------------
# TAB 5 - Strategic Scenarios (Phase 4, financial modeling -- deterministic)
# --------------------------------------------------------------------------
with tab_scenarios:
    st.markdown(f"#### Strategic Scenario Analysis — {PRIMARY_AGENCY}")
    st.warning(
        "**Hypothetical projection, not a forecast.** Everything in this tab is a "
        "deterministic calculation from assumptions *you* choose, anchored to the "
        "agency's real latest-year figures. It is not a prediction of what will actually "
        "happen, and no AI is involved in these calculations."
    )

    scenario_base_df = agency_kpis[agency_kpis["agency"] == PRIMARY_AGENCY].sort_values("year")
    suggested = suggest_reference_assumptions(scenario_base_df, lookback_years=5)
    st.caption(
        f"Reference starting point (computed from {PRIMARY_AGENCY}'s own trailing "
        f"5-year real CAGR, 2020–2025) — override any of these below: "
        f"ridership {suggested.ridership_growth_pct:+.1f}%/yr, "
        f"cost {suggested.cost_growth_pct:+.1f}%/yr, fares {suggested.fare_growth_pct:+.1f}%/yr."
    )

    c1, c2, c3, c4 = st.columns(4)
    ridership_growth = c1.slider("Ridership (UPT) growth, %/yr", -20.0, 20.0, float(suggested.ridership_growth_pct), 0.5)
    cost_growth = c2.slider("Operating cost growth, %/yr", -10.0, 20.0, float(suggested.cost_growth_pct), 0.5)
    fare_growth = c3.slider("Fare revenue growth, %/yr", -20.0, 20.0, float(suggested.fare_growth_pct), 0.5)
    years_ahead = c4.slider("Projection horizon, years", 1, 10, 5)

    assumptions = ScenarioAssumptions(
        ridership_growth_pct=ridership_growth,
        cost_growth_pct=cost_growth,
        fare_growth_pct=fare_growth,
        years_ahead=years_ahead,
    )
    projection = project_scenario(scenario_base_df, assumptions)
    summary = summarize_scenario(projection)

    st.divider()
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric(
        f"Projected cost per trip, {summary['final_year']}",
        fmt_money2(summary["cost_per_trip_final"]),
        f"{(summary['cost_per_trip_final']/summary['cost_per_trip_base']-1)*100:+.1f}% vs. {summary['base_year']} (real)",
    )
    sc2.metric(
        f"Projected farebox recovery, {summary['final_year']}",
        fmt_pct(summary["farebox_recovery_final"] * 100) if pd.notna(summary["farebox_recovery_final"]) else "n/a",
        f"{(summary['farebox_recovery_final']-summary['farebox_recovery_base'])*100:+.1f} pts vs. {summary['base_year']} (real)",
    )
    sc3.metric(
        f"Projected operating expense, {summary['final_year']}",
        fmt_money(projection.iloc[-1]["OpExp Total"]),
        f"{summary['opex_change_pct']:+.1f}% vs. {summary['base_year']} (real)",
    )

    fig_scenario = go.Figure()
    real_point = projection[~projection["is_projection"]]
    proj_points = projection[projection["is_projection"]]
    fig_scenario.add_trace(go.Scatter(
        x=real_point["year"], y=real_point["cost_per_trip"], mode="markers",
        name="Real (latest validated year)", marker=dict(color=ACCENT, size=12, symbol="diamond"),
    ))
    fig_scenario.add_trace(go.Scatter(
        x=pd.concat([real_point["year"], proj_points["year"]]),
        y=pd.concat([real_point["cost_per_trip"], proj_points["cost_per_trip"]]),
        mode="lines+markers", name="Hypothetical projection",
        line=dict(color=ACCENT, width=2, dash="dash"),
    ))
    fig_scenario.update_layout(
        title=f"Cost per trip: real anchor + hypothetical projection ({years_ahead}-year horizon)",
        xaxis_title="Report year", yaxis_title="Cost per trip ($)", template="plotly_white",
        height=400, margin=dict(t=60, b=40),
    )
    fig_scenario.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_scenario, use_container_width=True)

    with st.expander("Full projection table and assumptions"):
        display_proj = projection.rename(columns={
            "year": "Year", "OpExp Total": "Opex ($)", "UPT": "Trips", "Fares": "Fares ($)",
            "cost_per_trip": "Cost/trip ($)", "farebox_recovery": "Farebox recovery",
            "is_projection": "Hypothetical?",
        })[["Year", "Opex ($)", "Trips", "Fares ($)", "Cost/trip ($)", "Farebox recovery", "Hypothetical?"]]
        st.dataframe(
            display_proj.style.format({
                "Opex ($)": "${:,.0f}", "Trips": "{:,.0f}", "Fares ($)": "${:,.0f}",
                "Cost/trip ($)": "${:,.2f}", "Farebox recovery": "{:.1%}",
            }),
            hide_index=True, use_container_width=True,
        )
        st.caption(
            "Vehicle revenue miles/hours are held constant at the real latest-year level "
            "in this projection (no service-level assumption is modeled)."
        )

# --------------------------------------------------------------------------
# TAB 6 - Executive Consulting Report Generator (Phase 4, no AI required)
# --------------------------------------------------------------------------
SCENARIO_PRESETS = [
    "Reference trend (continue own 5-yr CAGR)",
    "Cost containment (cost growth capped at +2%/yr)",
    "Ridership recovery (+5%/yr ridership growth)",
]
BENCH_MODE_GROUPS = ["Rail", "Bus", "Demand Response"]

with tab_report:
    st.markdown("#### Executive Consulting Report Generator")
    st.caption(
        "Builds a management-consulting-style PowerPoint deck from the same real NTD data "
        "and deterministic calculations used throughout this app. No AI and no API key "
        "are required — this works identically whether or not Tab 7 is configured."
    )

    rc1, rc2, rc3, rc4 = st.columns(4)
    report_agency = rc1.selectbox("Agency", options=list(TARGET_AGENCIES.values()), index=list(TARGET_AGENCIES.values()).index(PRIMARY_AGENCY))
    report_agency_hist = agency_kpis[agency_kpis["agency"] == report_agency].sort_values("year")
    available_years = report_agency_hist["year"].astype(int).tolist()
    report_year = rc2.selectbox("Reporting year", options=available_years, index=len(available_years) - 1)
    scenario_choice = rc3.selectbox("Strategic scenario", options=SCENARIO_PRESETS)
    bench_mode_group = rc4.selectbox("Peer benchmark mode", options=BENCH_MODE_GROUPS, index=0)

    ref_assumptions = suggest_reference_assumptions(report_agency_hist, lookback_years=5)
    if scenario_choice == SCENARIO_PRESETS[0]:
        report_assumptions = ref_assumptions
    elif scenario_choice == SCENARIO_PRESETS[1]:
        report_assumptions = ScenarioAssumptions(
            ridership_growth_pct=ref_assumptions.ridership_growth_pct,
            cost_growth_pct=min(ref_assumptions.cost_growth_pct, 2.0),
            fare_growth_pct=ref_assumptions.fare_growth_pct,
            years_ahead=5,
        )
    else:
        report_assumptions = ScenarioAssumptions(
            ridership_growth_pct=max(ref_assumptions.ridership_growth_pct, 5.0),
            cost_growth_pct=ref_assumptions.cost_growth_pct,
            fare_growth_pct=ref_assumptions.fare_growth_pct,
            years_ahead=5,
        )

    report_projection = project_scenario(report_agency_hist, report_assumptions)
    report_summary = summarize_scenario(report_projection)

    report_bench = mode_group_year_kpis()
    report_bench = report_bench[
        (report_bench["mode_group"] == bench_mode_group)
        & (report_bench["agency"].isin(TARGET_AGENCIES.values()))
        & (report_bench["year"] <= report_year)
    ]
    report_findings = run_diagnostics(agency_kpis, list(TARGET_AGENCIES.values()), max(2015, report_year - 10), report_year)
    peer_list = [a for a in TARGET_AGENCIES.values() if a != report_agency]

    st.divider()
    st.markdown(
        f"**Preview:** {report_agency}, report year **{report_year}**, scenario "
        f"*“{scenario_choice}”* (ridership {report_assumptions.ridership_growth_pct:+.1f}%/yr, "
        f"cost {report_assumptions.cost_growth_pct:+.1f}%/yr, fares {report_assumptions.fare_growth_pct:+.1f}%/yr), "
        f"benchmarked on **{bench_mode_group}** service."
    )
    st.caption(
        "The deck includes: executive summary, financial & operational diagnostic, peer "
        "benchmarking, strategic scenario comparison, recommended priorities & risks, a "
        "90-day action plan with longer-term roadmap, and sources & methodology — 8 "
        "slides total, each tagged REAL DATA or HYPOTHETICAL."
    )

    if report_bench.empty:
        st.warning(f"{report_agency} has no {bench_mode_group} service to benchmark — choose a different mode above.")
    else:
        pptx_buffer = build_report(
            agency=report_agency,
            report_year=report_year,
            agency_history=report_agency_hist,
            mode_bench=report_bench,
            mode_group_label=bench_mode_group,
            peer_agencies=peer_list,
            findings=report_findings,
            assumptions=report_assumptions,
            projection=report_projection,
            scenario_summary=report_summary,
        )
        file_name = f"TransitStrategyIntelligence_{report_agency.replace(' ', '')}_{report_year}_ExecutiveReport.pptx"
        st.download_button(
            "\U0001F4E5 Download Executive Report (.pptx)",
            data=pptx_buffer,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
        )

# --------------------------------------------------------------------------
# TAB 7 - Strategic Consulting Advisor (Phase 4, fully deterministic, no AI)
# --------------------------------------------------------------------------
with tab_advisor:
    st.markdown("#### Strategic Consulting Advisor")
    st.caption(
        "Fully deterministic, rule-based engine — no external AI/LLM, no API key, and no "
        "internet access required beyond the initial setup. Turns the real diagnostic "
        "findings (Tab 4) and a hypothetical reference scenario into structured, "
        "evidence-based recommendations."
    )

    advisor_agency = st.selectbox("Agency", options=active_agencies, key="advisor_agency")
    advisor_hist = agency_kpis[agency_kpis["agency"] == advisor_agency].sort_values("year")
    advisor_assumptions = suggest_reference_assumptions(advisor_hist, lookback_years=5)
    advisor_projection = project_scenario(advisor_hist, advisor_assumptions)
    advisor_summary = summarize_scenario(advisor_projection)
    st.caption(
        f"Financial implications below use {advisor_agency}'s own reference scenario "
        f"(continuing its trailing 5-yr CAGR): ridership {advisor_assumptions.ridership_growth_pct:+.1f}%/yr, "
        f"cost {advisor_assumptions.cost_growth_pct:+.1f}%/yr, fares {advisor_assumptions.fare_growth_pct:+.1f}%/yr. "
        "Adjust your own assumptions in Tab 5 — Strategic Scenarios."
    )

    advisor_recs = generate_recommendations(
        advisor_agency, findings, advisor_assumptions, advisor_summary, max_recommendations=4
    )

    priority_badge = {"high": "\U0001F534 High priority", "medium": "\U0001F7E1 Medium priority", "low": "\U0001F7E2 Low priority"}
    for rec in advisor_recs:
        with st.expander(f"{priority_badge.get(rec.priority, rec.priority)} — {rec.title}"):
            st.markdown(f"**Owner:** {rec.owner_role}  \n**Target KPI:** {rec.target_kpi}")
            st.markdown(f"**Business problem:** {md_safe(rec.business_problem)}")
            st.markdown("**Supporting data (real, from NTD):**")
            for d in rec.supporting_data:
                st.markdown(f"- {md_safe(d)}")
            st.markdown("**Potential strategic actions:**")
            for a in rec.strategic_actions:
                st.markdown(f"- {a}")
            st.info(f"**Expected financial implications (hypothetical):** {md_safe(rec.financial_implications)}")
            st.markdown("**Implementation risks:**")
            for r in rec.risks:
                st.markdown(f"- {r}")
            st.markdown("**Additional information needed before this is a real decision:**")
            for info in rec.additional_info_needed:
                st.markdown(f"- {info}")

    st.divider()
    st.markdown("#### 90-day roadmap preview")
    advisor_roadmap = build_90_day_roadmap(advisor_recs)
    roadmap_df = pd.DataFrame(advisor_roadmap).rename(columns={
        "workstream": "Workstream", "owner_role": "Owner (role)",
        "day_30_milestone": "Day 30", "day_60_milestone": "Day 60",
        "day_90_milestone": "Day 90", "target_kpi": "Target KPI",
    })
    st.dataframe(roadmap_df, hide_index=True, use_container_width=True)
    st.caption(
        "The full 90-day action plan and longer-term roadmap, built from these same "
        "recommendations, are included in the Executive Report (Tab 6) PowerPoint download."
    )

# --------------------------------------------------------------------------
# TAB 8 - Methodology & Data Notes
# --------------------------------------------------------------------------
with tab_meta:
    st.markdown("#### Data source")
    st.markdown(
        """
        **FTA National Transit Database (NTD), TS2.1 -- Service Data and Operating Expenses
        Time Series by Mode** (2025 report year file), downloaded by the user and stored at
        `data/raw/`. See [`reports/phase2_data_quality_report.md`](reports/phase2_data_quality_report.md)
        for the full Phase 2 inspection of this workbook.
        """
    )

    st.markdown("#### Agencies covered")
    st.table(pd.DataFrame(
        [{"NTD ID": k, "Short name": v} for k, v in TARGET_AGENCIES.items()]
    ))

    st.markdown("#### KPI formulas")
    st.markdown(
        """
        | KPI | Formula | Notes |
        |---|---|---|
        | Total operating expense | Σ OpExp Total, operating modes | Agency-level view sums across all modes with `Mode_Status = Operating`. |
        | Annual passenger trips (UPT) | Σ UPT, operating modes | Unlinked passenger trips: one count per boarding. |
        | Cost per passenger trip | OpExp Total / UPT | |
        | Cost per vehicle revenue mile | OpExp Total / VRM | |
        | Trips per vehicle revenue hour | UPT / VRH | Core service-productivity KPI. |
        | Farebox recovery ratio | Fares / OpExp Total | Share of operating cost covered by fare revenue. |
        | Subsidy per trip | (OpExp Total − Fares) / UPT | |
        | Average trip length | PMT / UPT | PMT is Full-Reporter only; shown where available. |
        """
    )

    st.markdown("#### Caveats and limitations")
    st.markdown(
        """
        - **Nominal dollars.** No inflation adjustment is applied anywhere in this app. A
          rising cost-per-trip figure partly reflects general price inflation over 2015–2025,
          not solely agency-specific cost growth.
        - **Mode mix differs across agencies.** BART operates no bus service; Sacramento RT and
          LA Metro mix rail, bus, and demand-response service differently. All-modes totals
          (Executive Overview, Financial & Operational Performance tabs) are best used to track
          *each agency against its own history*, not to compare agencies head-to-head. Use the
          Peer Benchmarking tab's mode-group view for cross-agency comparisons.
        - **Missing values are left blank, never zero-filled.** A small number of newer/minor
          service rows (e.g. BART's eBART hybrid rail before it began operating, certain
          demand-response sub-service types) are null in early years because that service had
          not yet begun reporting -- these are excluded from sums for those years rather than
          treated as zero-cost, zero-ridership service.
        - **No root causes are asserted.** The Consulting Diagnostic Engine (Tab 4) reports
          observed evidence and clearly labeled hypotheses only. Confirming any hypothesis would
          require data not present in this workbook (e.g. cost indices, route-level detail,
          fare-policy records, service schedules).
        - **Historical findings (Tabs 1–4) use no AI/LLM analysis.** All figures, KPIs, and
          diagnostic findings are produced by deterministic calculations and rules against the
          real NTD data.
        - **Strategic Scenarios (Tab 5) are hypothetical, not forecasts.** They are
          deterministic projections from assumptions you choose, anchored to the agency's real
          latest-year figures. They do not account for policy changes, economic shocks, capital
          investment, or anything not captured by a constant annual growth rate.
        - **Executive Report (Tab 6) requires no AI/LLM and no API key.** The PowerPoint deck is
          built entirely with python-pptx from the same deterministic figures shown in Tabs 1–5
          and the same rule-based recommendations as Tab 7; every slide is tagged REAL DATA or
          HYPOTHETICAL.
        - **Strategic Consulting Advisor (Tab 7) uses no external AI/LLM.** It is a fixed,
          rule-based playbook keyed to the diagnostic finding types in Tab 4 -- the same inputs
          always produce the same recommendations. It introduces no new figures beyond the
          hypothetical scenario math already shown in Tab 5, and explicitly separates business
          problem, evidence, actions, financial implications, risks, and open questions.
        - **No internet access is required at runtime.** Once the app's data file and Python
          dependencies are installed, every chart, finding, scenario, recommendation, and report
          download works fully offline.
        """
    )

    st.divider()
    st.markdown("#### Disclaimer")
    st.caption(
        "TransitStrategy Intelligence is an independent portfolio project created to "
        "demonstrate data analysis, financial modeling, and application engineering skills. "
        "It is not affiliated with, endorsed by, or representing LA Metro, Sacramento "
        "Regional Transit, BART, the Federal Transit Administration, or any employer. It "
        "uses no external AI/LLM API. Historical figures are real, validated NTD data; "
        "scenario projections and rule-based recommendations are clearly labeled as "
        "hypothetical wherever they appear and should not be treated as professional "
        "consulting advice or official agency analysis."
    )
    st.caption("TransitStrategy Intelligence — Phase 4: Strategic Scenario Analysis and deterministic Strategic Consulting Advisor complete.")
