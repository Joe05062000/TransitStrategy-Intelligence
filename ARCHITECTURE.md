# TransitStrategy Intelligence — Architecture

*Turning Transit Data into Strategic Decisions*

This document reflects the project's production-ready target: a public, no-login
portfolio demonstration deployed on **Streamlit Community Cloud** from the planned
GitHub repository `TransitStrategy-Intelligence`, built on real FTA National Transit
Database (NTD) data. (The local project folder remains named `TransitStrategy-AI/`
to avoid breaking existing file paths.)

## Design goals

1. **Zero-friction access.** A recruiter opens a URL and immediately sees a
   working app with real data loaded — no account, no installs, no uploads,
   and no API key, ever.
2. **Fully self-contained.** No external AI/LLM API (Anthropic, OpenAI, or
   otherwise) is used anywhere in this application. Every chart, finding,
   scenario, recommendation, and report download is a deterministic
   calculation that runs locally and works fully offline once the app's data
   file and Python dependencies are installed.
3. **Real data, clearly separated from modeling.** Historical NTD figures,
   user-adjustable scenario assumptions, and rule-based strategic
   recommendations are visually and structurally distinct everywhere they
   appear together.
4. **Modules are separately testable.** Each layer below has its own module
   and its own test file; `app.py` only orchestrates Streamlit UI and calls
   into these modules.

## Module layout

```
TransitStrategy-AI/
├── app.py                      # Streamlit UI only — no business logic
├── src/
│   ├── ntd_loader.py            # Data processing: reads the raw NTD workbook
│   ├── kpi.py                   # Data processing: aggregation + KPI formulas
│   ├── diagnostics.py           # Analytics: rule-based historical findings (Phase 3)
│   ├── scenarios.py             # Financial modeling: user-assumption scenario engine (Phase 4)
│   ├── advisor.py               # Strategic Consulting Advisor: deterministic, rule-based (Phase 4)
│   └── report_generator.py      # Executive Report Generator: builds the .pptx deck (Phase 4)
├── data/
│   ├── raw/                     # Source NTD workbook, committed to the repo
│   └── processed/                # Reserved for future cached/derived extracts
├── reports/                     # Phase 2 data-quality report + generated executive reports
├── tests/                       # One test file per src/ module
├── .streamlit/
│   └── config.toml              # Theme / server config (committed; no secrets needed)
├── requirements.txt              # Pinned dependency versions (no AI/LLM SDK)
├── runtime.txt                   # Python version pin for Streamlit Cloud
├── ARCHITECTURE.md               # This file
├── DEPLOYMENT.md                 # Deployment checklist
└── README.md
```

### Data processing layer (`ntd_loader.py`, `kpi.py`)

Reads the real NTD TS2.1 workbook from `data/raw/`, reshapes it, and computes
every KPI used throughout the app. Pure functions over `pandas.DataFrame`,
cached with `st.cache_data`. No fabricated values: a missing or zero
denominator always produces `NaN`, never a silently invented number. Covered
by `tests/test_kpi.py`.

### Analytics layer (`diagnostics.py`)

The Phase 3 rule-based diagnostic engine. Produces findings strictly from
historical NTD figures, with every finding separating **evidence** (fact)
from an explicitly labeled, unconfirmed **hypothesis**. No AI involved.

### Financial modeling layer (`scenarios.py`, Phase 4)

A deterministic, transparent "what-if" scenario engine. Users adjust named
assumptions (e.g. ridership growth rate, cost growth rate, fare growth rate)
starting from the agency's own recent historical trend as a reference point;
the engine projects KPIs forward under those assumptions. Every scenario
output is labeled **"Hypothetical projection — not a forecast"** and shows
the assumptions used to produce it. No AI involved; fully covered by
`tests/test_scenarios.py`.

### Strategic Consulting Advisor (`advisor.py`, Phase 4)

A **fully deterministic, rule-based** engine — no external AI/LLM API, no
API key, no network call. A fixed playbook, keyed to each diagnostic
finding's rule type, turns real findings and the hypothetical scenario into
structured `Recommendation` objects, each explicitly separating:
business problem, supporting data (real), strategic actions, financial
implications (always labeled hypothetical), implementation risks, and what
additional information would be needed before treating it as a real
decision. The same inputs always produce the same output. Covered by
`tests/test_advisor.py`.

### Executive Report Generator (`report_generator.py`, Phase 4)

Builds an 8-slide PowerPoint deck with `python-pptx` from the same
deterministic outputs as the rest of the app (KPIs, diagnostic findings,
scenario projection, and the Strategic Consulting Advisor's recommendations
and 90-day roadmap). Every slide is tagged REAL DATA or HYPOTHETICAL. No AI
and no network access required. Covered by `tests/test_report_generator.py`.

## Data flow

```
data/raw/*.xlsx
   -> ntd_loader.load_long()         (per-sheet long format)
   -> kpi.load_master()              (pivoted wide, mode-level)
   -> kpi.agency_year_kpis() /       (aggregated + KPI formulas, cached)
      kpi.mode_group_year_kpis()
        |-- diagnostics.run_diagnostics()   -> historical findings (Tab 4)
        |-- scenarios.project_scenario()    -> hypothetical projections (Tab 5)
        |     \-- advisor.generate_recommendations()  -> Tab 7 + Executive Report (Tab 6)
        \-- app.py renders all of the above as Streamlit tabs
```

## Deployment target

Streamlit Community Cloud, deployed directly from this public (or
recruiter-shared private) GitHub repository. See `DEPLOYMENT.md` for the
step-by-step checklist. No database, no backend server, no user accounts,
and no external API of any kind — the entire app is a stateless Streamlit
script plus the committed NTD workbook.
