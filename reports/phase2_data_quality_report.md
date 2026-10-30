# Phase 2 Data Quality Report

**Source file:** `data/raw/2025 TS2.1 Service Data and Operating Expenses Time Series by Mode_260714.xlsx`
**Dataset:** FTA National Transit Database (NTD), TS2.1 — Service Data and Operating Expenses Time Series by Mode
**Report year:** 2025 (most recent annual report year in this file)
**Inspected:** openpyxl + pandas, read directly from the file — no values entered or altered.

## 1. Workbook structure

The file contains 13 sheets: one data dictionary (`Read Me - Data Dictionary`) and 12 metric
sheets. Every metric sheet shares an identical schema:

- **16 identifier/metadata columns** (agency and service identification):
  `Last Report Year, NTD ID, Agency Name, Agency Status, Reporter Type, Reporting Module,
  City, State, Census Year, Primary UZA Name, UACE Code, UZA Area SQ Miles, UZA Population,
  Mode_Status, Mode, Type of Service`
- **11 annual value columns**, one per report year: `2015 <metric> … 2025 <metric>`

Each sheet has 4,900 rows (one row per agency × mode × type-of-service combination) covering
2,572 unique NTD-ID agencies nationwide.

| Sheet | Contents | Reporter types it applies to |
|---|---|---|
| OpExp Total | Total operating expenses | Full, Reduced, Separate Service |
| OpExp VO | Operating expense — Vehicle Operations | Full Reporters only |
| OpExp VM | Operating expense — Vehicle Maintenance | Full Reporters only |
| OpExp NVM | Operating expense — Non-Vehicle Maintenance | Full Reporters only |
| OpExp GA | Operating expense — General Administration | Full Reporters only |
| Fares | Fare revenue earned | Full, Reduced, Separate Service |
| DRM | Directional route miles | Full Reporters only |
| VOMS | Vehicles operated in maximum service | Full, Reduced |
| VRM | Vehicle revenue miles | Full, Reduced |
| VRH | Vehicle revenue hours | Full, Reduced |
| UPT | Unlinked passenger trips | Full, Reduced |
| PMT | Passenger miles traveled | Full Reporters only |

## 2. Reporting-year coverage

- **Time series:** 2015–2025 (11 consecutive annual report years) in every metric sheet.
- **2025** is the most recent report year and the only year with **zero missing values**
  across all three target agencies' active service modes.
- Nationwide, null rates in the OpExp VO/VM/NVM/GA and PMT sheets are high (~70–73%) because,
  per the data dictionary, those four expense breakdowns and PMT are **only required from
  Full Reporters** — Rural, Reduced, and Reduced Asset Reporters (the majority of the 2,572
  agencies) leave them blank by design, not due to a data error.

## 3. Transportation modes present

19 mode codes appear in the file: `AR, CB, CC, CR, DR, FB, HR, IP, LR, MB, MG, OR, PB, RB, SR,
TB, TR, VP, YR` (Alaska Railroad, Commuter Bus, Cable Car, Commuter Rail, Demand Response,
Ferryboat, Heavy Rail, Inclined Plane, Light Rail, Bus, Monorail/Automated Guideway, Other
Rail, Publico, Bus Rapid Transit, Streetcar Rail, Trolleybus, Aerial Tramway, Vanpool, Hybrid
Rail). Full definitions are in the `Read Me - Data Dictionary` sheet.

Type-of-service codes: `DO` (directly operated), `PT` (purchased transportation), `TN`
(taxi), `TX` (other demand-response arrangement).

## 4. Target agency identification

| Agency | NTD ID | City/State | Reporter Type | Status | Primary UZA (2020 pop.) |
|---|---|---|---|---|---|
| **LA Metro** — Los Angeles County Metropolitan Transportation Authority (LACMTA) | 90154 | Los Angeles, CA | Full Reporter | Active | Los Angeles–Long Beach–Anaheim, CA (12,237,376) |
| **Sacramento Regional Transit District** | 90019 | Sacramento, CA | Full Reporter | Active | Sacramento, CA (1,946,618) |
| **BART** — San Francisco Bay Area Rapid Transit District | 90003 | Oakland, CA | Full Reporter | Active | San Francisco–Oakland, CA (3,515,933) |

All three are **Active Full Reporters** with a `Last Report Year` of 2025 — the highest tier
of NTD reporting, so all 12 metric sheets apply to each of them in full.

### Modes operated by each agency (2025, `Mode_Status = Operating`)

- **LA Metro (90154):** DR/DO, DR/PT, HR/DO (Heavy Rail), LR/DO (Light Rail), MB/DO (Bus),
  MB/PT, RB/DO (Bus Rapid Transit), VP/PT — 8 active mode/service rows.
- **Sacramento RT (90019):** DR/DO, DR/PT, DR/TN, LR/DO (Light Rail), MB/DO (Bus) — 5 active
  mode/service rows (plus 3 discontinued legacy rows: CB/PT, DR/TX, MB/PT, which carry no
  values).
- **BART (90003):** HR/DO (Heavy Rail), MG/PT (Monorail/AGT — the Oakland Airport Connector),
  YR/DO (Hybrid Rail — eBART) — 3 active mode/service rows (plus a discontinued MB/PT row).

## 5. Data-quality findings for the three target agencies

- **2025 completeness: 100%.** Every active (`Operating`) mode row for LA Metro, Sacramento RT,
  and BART has a non-null value in every one of the 12 metric sheets for report year 2025.
- **Historical completeness (2015–2024): high, with explainable gaps.** A small number of
  mode/service rows are null in earlier years, and only in earlier years:
  - BART's YR (eBART, hybrid rail) — null through 2017, populated from the year that service began.
  - Sacramento RT's DR/PT and DR/TN rows — null in most early years, populated only once that
    specific demand-response sub-service began being reported separately.
  - LA Metro's DR/DO and DR/PT rows — null in several early years, same pattern.
  - All of these are **minor/newer service lines**, not core modes. The core modes for each
    agency (BART: HR; Sacramento RT: LR, MB; LA Metro: HR, LR, MB, RB) have **zero missing
    values across all 11 years**.
- **Discontinued rows carry no values**, by design (e.g., Sacramento RT's legacy CB/PT row,
  BART's legacy MB/PT row) — these are retired modes, not missing data.
- **No fabricated, estimated, or interpolated values were introduced** at any point in this
  inspection. Every figure referenced above was read directly from the workbook.

## 6. KPIs that can be calculated from this data today

Because UPT, PMT, VRM, VRH, VOMS, DRM, Fares, and all four OpExp components are complete for
2025 (and nearly complete back to 2015) for all three target agencies, the following
consulting-grade KPIs can be calculated **without any additional data**:

**Financial / cost efficiency**
- Operating cost per unlinked passenger trip (`OpExp Total / UPT`)
- Operating cost per vehicle revenue mile and per vehicle revenue hour (`OpExp Total / VRM`, `/ VRH`)
- Operating cost per passenger mile (`OpExp Total / PMT`)
- Farebox recovery ratio (`Fares / OpExp Total`)
- Cost structure mix — share of total cost by function (`OpExp VO/VM/NVM/GA ÷ OpExp Total`)
- Subsidy per passenger trip (`(OpExp Total − Fares) / UPT`)

**Ridership / service effectiveness**
- Passengers per vehicle revenue hour and per vehicle revenue mile (`UPT / VRH`, `UPT / VRM`)
- Average trip length (`PMT / UPT`)
- Fare revenue per passenger trip (`Fares / UPT`)

**Service delivery / asset utilization**
- Vehicle revenue miles and hours per vehicle operated in maximum service (`VRM / VOMS`, `VRH / VOMS`)
- Service intensity per directional route mile (`VRM / DRM`, `UPT / DRM`)

**Benchmarking (all of the above)**
- Each KPI can be computed per agency, per mode, and per year (2015–2025), enabling:
  - Trend analysis (e.g., LA Metro HR ridership recovery since 2020)
  - Peer benchmarking across LA Metro, Sacramento RT, and BART, and against any of the other
    2,569 reporting agencies in the file
  - Mode-mix comparison (e.g., BART's heavy-rail-dominant model vs. LA Metro's multimodal mix)

**Out of scope for this workbook** (would require other NTD data tables not present in this
file): on-time performance, safety/incident data, asset condition/state of good repair,
capital expenditures, farebox pricing/fare structure detail, employee headcount, and
demographic/equity data.

## 7. What was *not* done (per instructions)

- No data was fabricated, estimated, or backfilled.
- No dashboard or visualization was built.
- No Phase 3 (app integration) work was started.
