"""Loader for the FTA NTD TS2.1 Service Data and Operating Expenses Time Series workbook."""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

ID_COLS = [
    "Last Report Year",
    "NTD ID",
    "Agency Name",
    "Agency Status",
    "Reporter Type",
    "Reporting Module",
    "City",
    "State",
    "Census Year",
    "Primary UZA Name",
    "UACE Code",
    "UZA Area SQ Miles",
    "UZA Population",
    "Mode_Status",
    "Mode",
    "Type of Service",
]

METRIC_SHEETS = [
    "OpExp Total",
    "OpExp VO",
    "OpExp VM",
    "OpExp NVM",
    "OpExp GA",
    "Fares",
    "DRM",
    "VOMS",
    "VRM",
    "VRH",
    "UPT",
    "PMT",
]


def find_workbook() -> Path:
    candidates = sorted(
        p for p in RAW_DIR.glob("*TS2.1*Service Data*.xlsx") if not p.name.startswith((".", "~"))
    )
    if not candidates:
        raise FileNotFoundError(f"No TS2.1 workbook found in {RAW_DIR}")
    return candidates[0]


def load_sheet(sheet_name: str, path: Path | None = None) -> pd.DataFrame:
    path = path or find_workbook()
    return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")


def load_long(sheet_name: str, path: Path | None = None) -> pd.DataFrame:
    """Load one metric sheet and reshape the year columns into a tidy long format."""
    df = load_sheet(sheet_name, path)
    year_cols = [c for c in df.columns if c not in ID_COLS]
    long_df = df.melt(
        id_vars=ID_COLS,
        value_vars=year_cols,
        var_name="year_col",
        value_name="value",
    )
    long_df["year"] = long_df["year_col"].str.extract(r"(\d{4})").astype(int)
    long_df["metric"] = sheet_name
    long_df = long_df.drop(columns=["year_col"])
    return long_df
