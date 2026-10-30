# Deployment Checklist — TransitStrategy Intelligence (Streamlit Community Cloud)

**Status: not yet deployed.** This checklist is prepared so deployment is a
mechanical, low-risk step whenever it is approved.

**Planned GitHub repository name:** `TransitStrategy-Intelligence`. (The local
project folder stays named `TransitStrategy-AI/` to avoid breaking existing
file paths — the rename happens on GitHub, not locally.)

## 1. Repository readiness

- [x] `data/raw/*.xlsx` committed to the repo (7.1 MB — well under GitHub's
      100 MB hard limit and 50 MB soft-warning threshold; no Git LFS needed).
- [x] `ntd_loader.find_workbook()` uses a path relative to the repo root
      (`Path(__file__).resolve().parent.parent / "data" / "raw"`), so it
      resolves correctly regardless of the working directory Streamlit
      Cloud launches from.
- [x] `.gitignore` excludes `.venv/` and `__pycache__/`.
- [ ] Repository pushed to GitHub as `TransitStrategy-Intelligence` (public,
      or private with the recruiter added as a collaborator if the live URL
      alone isn't sufficient).

## 2. Dependency pinning

- [x] `requirements.txt` pins exact versions (not `>=`) so Streamlit Cloud's
      build reproduces the environment this app was tested against.
- [x] No AI/LLM SDK (Anthropic, OpenAI, or otherwise) is listed as a
      dependency — the app has no external API dependency of any kind.
- [x] `runtime.txt` pins the Python version (`python-3.12`) — Streamlit
      Cloud reads this to select the build image.
- [ ] After the first cloud build, confirm no dependency resolution warnings
      in the Streamlit Cloud build log.

## 3. Secrets management

- [x] **None required.** This application needs no API keys, tokens, or
      other secrets to run any feature, including the PowerPoint report
      generator and the Strategic Consulting Advisor — both are fully
      deterministic and local. There is nothing to configure under
      **App settings → Secrets** in the Streamlit Cloud dashboard.

## 4. File paths and portability

- [x] No absolute local paths anywhere in `src/` or `app.py` — everything is
      derived from `Path(__file__).resolve()`.
- [x] No writes to the local filesystem at runtime (reports are generated
      in-memory and offered via `st.download_button`, not written to disk).

## 5. Offline / no-internet-at-runtime verification

- [x] No module in `src/` imports a network client (`requests`, `httpx`,
      `anthropic`, `openai`, etc.) or makes any outbound HTTP call —
      verified by `tests/test_advisor.py::test_advisor_module_imports_no_network_or_ai_dependency`
      and `tests/test_report_generator.py::test_report_works_without_any_ai_import`.
- [x] Every dashboard, calculation, recommendation, and report download
      works with the network disabled, as long as the data file and Python
      dependencies from `requirements.txt` were installed beforehand.

## 6. Resource limits

- Streamlit Community Cloud free tier: ~1 GB RAM per app. The master
  dataset (3 agencies, 12 metrics, 11 years) is a few thousand rows —
  trivial memory footprint. `st.cache_data` prevents re-reading the 7 MB
  workbook on every interaction.
- Cold-start load time: reading and pivoting the workbook takes a few
  seconds on first load; subsequent interactions are served from cache.

## 7. Pre-launch smoke test (run locally before every deploy)

```bash
python3 -m pytest tests/ -q
streamlit run app.py
```

Click through all tabs, confirm:
- The app loads with **zero configuration** — no secrets file, no
  environment variables — and every tab works normally.
- The Home tab, disclaimer, and methodology notes render correctly.
- Year-range slider and agency filters update all charts live.
- The Strategic Consulting Advisor (Tab 7) produces recommendations and the
  Executive Report (Tab 6) downloads a valid `.pptx`, both with no network
  access.

## 8. Go-live steps (when approved)

1. Push the repository to GitHub as `TransitStrategy-Intelligence`.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at the `TransitStrategy-Intelligence` repo, branch `main`, main
   file `app.py`.
3. No secrets to add — skip straight to Deploy.
4. Deploy, then re-run the smoke test above against the live URL.
5. Share the URL.
