"""Executive Consulting Report Generator (Phase 4).

Builds a management-consulting-style PowerPoint deck from:
  - real, validated FTA NTD figures (historical diagnostic slides),
  - a user-configured hypothetical financial scenario (clearly labeled), and
  - the deterministic, rule-based Strategic Consulting Advisor (src/advisor.py)
    for the recommended-priorities and 90-day-roadmap slides.

No AI/LLM, no API key, and no network access are involved anywhere in this
module or its dependencies -- it works fully offline once python-pptx and
the other pinned requirements are installed.

Every slide that shows a number is tagged REAL DATA or HYPOTHETICAL in its
top-right corner, and the final "Sources & Methodology" slide documents
exactly where every figure came from.
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

from advisor import build_90_day_roadmap, generate_recommendations
from diagnostics import Finding
from kpi import MODE_LABELS
from scenarios import ScenarioAssumptions

# -- Visual language -----------------------------------------------------
NAVY = RGBColor(0x1A, 0x1A, 0x2E)
ACCENT = RGBColor(0x0B, 0x5F, 0xFF)
AMBER = RGBColor(0xE0, 0x8A, 0x00)
GREEN = RGBColor(0x1F, 0x9D, 0x55)
GREY = RGBColor(0x5A, 0x5A, 0x6E)
LIGHT_BG = RGBColor(0xF3, 0xF5, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xC0, 0x30, 0x30)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.55)


def _blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]  # blank layout in the default template
    return prs.slides.add_slide(layout)


def _textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    return tf


def _badge(slide, label: str, hypothetical: bool):
    color = AMBER if hypothetical else GREEN
    text = "HYPOTHETICAL" if hypothetical else "REAL DATA"
    box = slide.shapes.add_textbox(SLIDE_W - Inches(2.2), Inches(0.3), Inches(1.8), Inches(0.4))
    tf = box.text_frame
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = f"{label + ': ' if label else ''}{text}"
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = color


def _title(slide, text: str, subtitle: str | None = None):
    tf = _textbox(slide, MARGIN, Inches(0.25), SLIDE_W - Inches(2.9), Inches(1.1))
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.color.rgb = NAVY
    if subtitle:
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = subtitle
        r2.font.size = Pt(13)
        r2.font.color.rgb = GREY


def _footer(slide, agency: str, page_no: int):
    tf = _textbox(slide, MARGIN, SLIDE_H - Inches(0.45), SLIDE_W - 2 * MARGIN, Inches(0.35))
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = (
        f"TransitStrategy Intelligence — independent portfolio project, not an official {agency} "
        f"or FTA document  ·  {date.today().isoformat()}  ·  {page_no}"
    )
    run.font.size = Pt(8.5)
    run.font.color.rgb = GREY


def _bullets(slide, left, top, width, height, items: list[str], size=14, color=NAVY):
    tf = _textbox(slide, left, top, width, height)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(8)


def _table(slide, left, top, width, height, df: pd.DataFrame, header_color=ACCENT):
    rows, cols = df.shape[0] + 1, df.shape[1]
    graphic_frame = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = graphic_frame.table
    for c, col_name in enumerate(df.columns):
        cell = table.cell(0, c)
        cell.text = str(col_name)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_color
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = WHITE
    for r in range(df.shape[0]):
        for c in range(cols):
            cell = table.cell(r + 1, c)
            cell.text = str(df.iat[r, c])
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT_BG if r % 2 == 0 else WHITE
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10.5)
                p.font.color.rgb = NAVY
    return table


def _line_chart(slide, left, top, width, height, categories, series: dict[str, list[float]], y_fmt="General"):
    data = CategoryChartData()
    data.categories = [str(c) for c in categories]
    for name, values in series.items():
        data.add_series(name, values)
    gframe = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, left, top, width, height, data)
    chart = gframe.chart
    chart.has_legend = len(series) > 1
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    chart.value_axis.tick_labels.number_format = y_fmt
    chart.value_axis.tick_labels.number_format_is_linked = False
    return chart


def _bar_chart(slide, left, top, width, height, categories, series: dict[str, list[float]], y_fmt="General"):
    data = CategoryChartData()
    data.categories = [str(c) for c in categories]
    for name, values in series.items():
        data.add_series(name, values)
    gframe = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width, height, data)
    chart = gframe.chart
    chart.has_legend = len(series) > 1
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    chart.value_axis.tick_labels.number_format = y_fmt
    chart.value_axis.tick_labels.number_format_is_linked = False
    return chart


def _pick_headline_finding(findings: list[Finding], agency: str) -> str:
    agency_findings = [f for f in findings if f.agency == agency]
    if not agency_findings:
        return f"{agency}: no material performance flags identified in the selected period"
    severity_order = {"high": 0, "medium": 1, "low": 2}
    agency_findings.sort(key=lambda f: severity_order.get(f.severity, 3))
    return agency_findings[0].title


def build_report(
    agency: str,
    report_year: int,
    agency_history: pd.DataFrame,
    mode_bench: pd.DataFrame,
    mode_group_label: str,
    peer_agencies: list[str],
    findings: list[Finding],
    assumptions: ScenarioAssumptions,
    projection: pd.DataFrame,
    scenario_summary: dict,
) -> io.BytesIO:
    """Builds the full executive deck and returns it as an in-memory .pptx file.

    Parameters mirror exactly what the Streamlit UI already computes
    deterministically (via kpi.py, diagnostics.py, scenarios.py) -- this
    function performs no calculations of its own beyond simple table/chart
    formatting, and introduces no new figures.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    page = 0

    hist = agency_history.sort_values("year")
    latest = hist[hist["year"] == report_year]
    latest = latest.iloc[0] if not latest.empty else hist.iloc[-1]
    actual_year = int(latest["year"])

    # ---- Slide 1: Title -------------------------------------------------
    s = _blank_slide(prs)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    tf_brand = _textbox(s, Inches(0.8), Inches(1.75), Inches(11.7), Inches(0.5))
    p_brand = tf_brand.paragraphs[0]
    r_brand = p_brand.add_run()
    r_brand.text = "TRANSITSTRATEGY INTELLIGENCE  ·  Turning Transit Data into Strategic Decisions"
    r_brand.font.size = Pt(13)
    r_brand.font.bold = True
    r_brand.font.color.rgb = RGBColor(0x9D, 0xC4, 0xFF)

    tf = _textbox(s, Inches(0.8), Inches(2.3), Inches(11.7), Inches(1.4))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "Executive Performance Diagnostic"
    r.font.size = Pt(40)
    r.font.bold = True
    r.font.color.rgb = WHITE
    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = agency
    r2.font.size = Pt(26)
    r2.font.color.rgb = RGBColor(0x9D, 0xC4, 0xFF)

    tf2 = _textbox(s, Inches(0.8), Inches(4.3), Inches(11.7), Inches(1.5))
    p3 = tf2.paragraphs[0]
    r3 = p3.add_run()
    r3.text = (
        f"Report year {actual_year}  ·  Benchmarked against {', '.join(peer_agencies) or 'no peer agencies'}\n"
        f"Source: FTA National Transit Database (NTD), TS2.1\n"
        f"Generated {date.today().isoformat()}"
    )
    r3.font.size = Pt(14)
    r3.font.color.rgb = RGBColor(0xC6, 0xCC, 0xDA)

    tf3 = _textbox(s, Inches(0.8), Inches(6.5), Inches(11.7), Inches(0.7))
    p4 = tf3.paragraphs[0]
    r4 = p4.add_run()
    r4.text = (
        "Independent portfolio project — not affiliated with, endorsed by, or representing "
        f"{agency}, the FTA, or any employer. Historical figures are real; scenario "
        "projections and recommendations are explicitly labeled as hypothetical."
    )
    r4.font.size = Pt(10.5)
    r4.font.italic = True
    r4.font.color.rgb = RGBColor(0x9A, 0xA3, 0xBD)
    page += 1

    # ---- Slide 2: Executive summary & key findings ----------------------
    s = _blank_slide(prs)
    headline = _pick_headline_finding(findings, agency)
    _title(s, headline, "Executive summary — key findings from real, validated NTD data")
    _badge(s, "", hypothetical=False)

    kpi_rows = [
        ["Total operating expense", f"${latest['OpExp Total']:,.0f}"],
        ["Annual passenger trips (UPT)", f"{latest['UPT']:,.0f}"],
        ["Cost per passenger trip", f"${latest['cost_per_trip']:.2f}"],
        ["Cost per vehicle revenue mile", f"${latest['cost_per_vrm']:.2f}"],
        ["Trips per vehicle revenue hour", f"{latest['trips_per_vrh']:.2f}"],
        ["Farebox recovery ratio", f"{latest['farebox_recovery']*100:.1f}%"],
    ]
    kpi_df = pd.DataFrame(kpi_rows, columns=["KPI", f"{actual_year} value"])
    _table(s, MARGIN, Inches(1.6), Inches(5.2), Inches(3.0), kpi_df)

    agency_findings = [f for f in findings if f.agency == agency][:4]
    bullet_items = [f"{f.title.split(': ', 1)[-1]}" for f in agency_findings] or [
        "No material performance flags identified for the selected period under current thresholds."
    ]
    _bullets(s, Inches(6.1), Inches(1.6), Inches(6.7), Inches(4.5), bullet_items, size=14)
    _footer(s, agency, (page := page + 1))

    # ---- Slide 3: Financial & operational performance diagnostic --------
    s = _blank_slide(prs)
    _title(s, f"{agency}: cost and ridership have diverged since 2015", "Financial & operational performance diagnostic")
    _badge(s, "", hypothetical=False)
    years = hist["year"].astype(int).tolist()
    _line_chart(
        s, MARGIN, Inches(1.6), Inches(7.3), Inches(3.0), years,
        {"Cost per trip ($)": hist["cost_per_trip"].round(2).tolist()},
        y_fmt="$#,##0.00",
    )
    recent = hist.tail(5)[["year", "OpExp Total", "UPT", "cost_per_trip", "trips_per_vrh", "farebox_recovery"]].copy()
    recent["year"] = recent["year"].astype(int)
    recent_fmt = pd.DataFrame({
        "Year": recent["year"],
        "Opex ($M)": (recent["OpExp Total"] / 1e6).round(1),
        "Trips (M)": (recent["UPT"] / 1e6).round(1),
        "Cost/trip": recent["cost_per_trip"].round(2),
        "Trips/VRH": recent["trips_per_vrh"].round(1),
        "Farebox": (recent["farebox_recovery"] * 100).round(1).astype(str) + "%",
    })
    _table(s, Inches(8.0), Inches(1.6), Inches(4.8), Inches(3.3), recent_fmt)
    _bullets(
        s, MARGIN, Inches(5.0), SLIDE_W - 2 * MARGIN, Inches(1.8),
        [f.title.split(": ", 1)[-1] for f in agency_findings[:2]] or ["No material flags in this period."],
        size=13, color=GREY,
    )
    _footer(s, agency, (page := page + 1))

    # ---- Slide 4: Peer benchmarking --------------------------------------
    s = _blank_slide(prs)
    _title(
        s, f"{mode_group_label} mode comparison: where {agency} stands against peers",
        f"Peer benchmarking — {mode_group_label} service only (like-for-like comparison)",
    )
    _badge(s, "", hypothetical=False)
    bench_years_latest = mode_bench[mode_bench["year"] == mode_bench["year"].max()]
    if not bench_years_latest.empty:
        cats = bench_years_latest["agency"].tolist()
        _bar_chart(
            s, MARGIN, Inches(1.6), Inches(6.0), Inches(3.2), cats,
            {"Cost per trip ($)": bench_years_latest["cost_per_trip"].round(2).tolist()},
            y_fmt="$#,##0.00",
        )
        bench_table = pd.DataFrame({
            "Agency": bench_years_latest["agency"],
            "Opex ($M)": (bench_years_latest["OpExp Total"] / 1e6).round(1),
            "Trips (M)": (bench_years_latest["UPT"] / 1e6).round(1),
            "Cost/trip": bench_years_latest["cost_per_trip"].round(2),
            "Farebox": (bench_years_latest["farebox_recovery"] * 100).round(1).astype(str) + "%",
        })
        _table(s, Inches(7.3), Inches(1.6), Inches(5.5), Inches(2.4), bench_table)
    _bullets(
        s, MARGIN, Inches(5.1), SLIDE_W - 2 * MARGIN, Inches(1.8),
        [
            f"Comparison restricted to {mode_group_label} service only — agencies differ substantially "
            "in mode mix, so all-modes totals would conflate mode mix with performance.",
            "A KPI gap is informative but not, by itself, proof of better or worse management — it is a "
            "starting point for further investigation (see Tab 4 hypotheses).",
        ],
        size=12.5, color=GREY,
    )
    _footer(s, agency, (page := page + 1))

    # ---- Slide 5: Strategic alternatives & scenario comparison -----------
    s = _blank_slide(prs)
    _title(
        s, f"Under these assumptions, {agency}'s cost per trip could reach "
           f"${scenario_summary['cost_per_trip_final']:.2f} by {scenario_summary['final_year']}",
        "Strategic alternatives — hypothetical financial scenario, not a forecast",
    )
    _badge(s, "", hypothetical=True)
    proj_years = projection["year"].astype(int).tolist()
    _line_chart(
        s, MARGIN, Inches(1.7), Inches(7.3), Inches(3.0), proj_years,
        {"Cost per trip ($)": projection["cost_per_trip"].round(2).tolist()},
        y_fmt="$#,##0.00",
    )
    assum_df = pd.DataFrame([
        ["Ridership (UPT) growth", f"{assumptions.ridership_growth_pct:+.1f}%/yr"],
        ["Operating cost growth", f"{assumptions.cost_growth_pct:+.1f}%/yr"],
        ["Fare revenue growth", f"{assumptions.fare_growth_pct:+.1f}%/yr"],
        ["Horizon", f"{assumptions.years_ahead} years ({scenario_summary['base_year']}–{scenario_summary['final_year']})"],
        ["Service levels (VRM/VRH)", "Held constant (no assumption modeled)"],
    ], columns=["Assumption", "Value"])
    _table(s, Inches(8.0), Inches(1.7), Inches(4.8), Inches(2.6), assum_df, header_color=AMBER)
    _bullets(
        s, MARGIN, Inches(5.0), SLIDE_W - 2 * MARGIN, Inches(1.9),
        [
            f"Real {scenario_summary['base_year']} cost per trip: ${scenario_summary['cost_per_trip_base']:.2f} "
            f"→ hypothetical {scenario_summary['final_year']} projection: ${scenario_summary['cost_per_trip_final']:.2f}.",
            "This is a constant-growth-rate projection, not a forecast: it does not model policy changes, "
            "economic shocks, service redesign, or capital investment.",
        ],
        size=12.5, color=GREY,
    )
    _footer(s, agency, (page := page + 1))

    # ---- Slide 6: Recommended priorities, assumptions, risks -------------
    # Generated by the deterministic, rule-based Strategic Consulting Advisor
    # (src/advisor.py) -- no AI/LLM involved.
    recommendations = generate_recommendations(
        agency, findings, assumptions, scenario_summary, max_recommendations=3
    )
    s = _blank_slide(prs)
    _title(s, f"Recommended priorities for {agency} leadership", "Directions for further investigation, not final decisions")
    _badge(s, "", hypothetical=True)
    priorities = [f"{r.title} (owner: {r.owner_role})" for r in recommendations]
    _bullets(s, MARGIN, Inches(1.6), Inches(6.1), Inches(2.9), priorities, size=13.5)

    risks = list(dict.fromkeys(r for rec in recommendations for r in rec.risks))[:5] or [
        "No material risks flagged under current thresholds."
    ]
    _bullets(s, Inches(6.5), Inches(1.6), Inches(6.3), Inches(2.9), risks, size=12, color=RED)
    tf_lbl = _textbox(s, Inches(6.5), Inches(1.2), Inches(4), Inches(0.4))
    r_lbl = tf_lbl.paragraphs[0].add_run()
    r_lbl.text = "Key risks / limitations"
    r_lbl.font.bold = True
    r_lbl.font.size = Pt(13)
    r_lbl.font.color.rgb = RED

    info_needed = list(dict.fromkeys(i for rec in recommendations for i in rec.additional_info_needed))[:4]
    if info_needed:
        _bullets(s, MARGIN, Inches(4.9), SLIDE_W - 2 * MARGIN, Inches(1.8), info_needed, size=11.5, color=GREY)
        tf_lbl2 = _textbox(s, MARGIN, Inches(4.55), Inches(6), Inches(0.4))
        r_lbl2 = tf_lbl2.paragraphs[0].add_run()
        r_lbl2.text = "Additional information needed before these are real decisions"
        r_lbl2.font.bold = True
        r_lbl2.font.size = Pt(12)
        r_lbl2.font.color.rgb = GREY
    _footer(s, agency, (page := page + 1))

    # ---- Slide 7: 90-day action plan & roadmap ---------------------------
    s = _blank_slide(prs)
    _title(s, f"Proposed path forward for {agency}", "90-day action plan and longer-term implementation roadmap")
    _badge(s, "", hypothetical=True)

    roadmap_rows = build_90_day_roadmap(recommendations)
    roadmap_df = pd.DataFrame([
        [r["workstream"], r["owner_role"], r["day_30_milestone"], r["day_60_milestone"], r["day_90_milestone"], r["target_kpi"]]
        for r in roadmap_rows
    ], columns=["Workstream", "Owner (role)", "Day 30", "Day 60", "Day 90", "Target KPI"])
    _table(s, MARGIN, Inches(1.6), SLIDE_W - 2 * MARGIN, Inches(2.6), roadmap_df, header_color=ACCENT)

    longer_term = [
        "6–12 months: Pilot the highest-confidence improvement option(s) on a limited scope; measure "
        "against the Target KPIs above.",
        "12–18 months: Expand successful pilots; re-run this diagnostic to confirm the trend has responded.",
        "Ongoing: Institutionalize quarterly tracking of the KPIs in this report against peer benchmarks.",
    ]
    tf_lbl3 = _textbox(s, MARGIN, Inches(4.5), Inches(6), Inches(0.4))
    r_lbl3 = tf_lbl3.paragraphs[0].add_run()
    r_lbl3.text = "Longer-term roadmap"
    r_lbl3.font.bold = True
    r_lbl3.font.size = Pt(13)
    r_lbl3.font.color.rgb = NAVY
    _bullets(s, MARGIN, Inches(4.9), SLIDE_W - 2 * MARGIN, Inches(2.0), longer_term, size=13)
    _footer(s, agency, (page := page + 1))

    # ---- Slide 8: Sources & methodology -----------------------------------
    s = _blank_slide(prs)
    _title(s, "Sources & methodology", "Every figure in this report traces to one of these sources")
    methodology = [
        "Historical data: FTA National Transit Database (NTD), TS2.1 — Service Data and Operating "
        "Expenses Time Series by Mode (2025 report year file), covering 2015–2025.",
        "KPI formulas: cost per trip = Total Opex / UPT; cost per VRM = Total Opex / VRM; "
        "trips per VRH = UPT / VRH; farebox recovery = Fares / Total Opex.",
        "Peer benchmarking is restricted to a single mode group (rail-to-rail, bus-to-bus) to avoid "
        "conflating differences in mode mix with differences in performance.",
        "Strategic scenario (Slide 5) is a deterministic, constant-growth-rate projection from "
        "user-chosen assumptions — not a statistical forecast and not AI-generated.",
        "No AI/LLM was used to generate any figure, chart, or recommendation in this report. "
        "Report generation requires no API key or external service.",
        "This report is an independent portfolio project and is not an official publication of "
        f"{agency}, the FTA, or any other organization.",
    ]
    _bullets(s, MARGIN, Inches(1.6), SLIDE_W - 2 * MARGIN, Inches(5.0), methodology, size=13.5)
    _footer(s, agency, (page := page + 1))

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
