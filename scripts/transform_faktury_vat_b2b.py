#!/usr/bin/env python3
"""Transform Faktury VAT sprzedaży.csv into B2B invoice summary Excel."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

COLS = [
    "Data",
    "Typ",
    "Numer",
    "TypDok",
    "Nabywca",
    "Netto",
    "Brutto",
    "Wartosc",
    "Waluta",
    "Kategoria",
    "NIP",
    "VATIN",
    "StatusKSeF",
]

MONTH_PL = {
    1: "styczeń",
    2: "luty",
    3: "marzec",
    4: "kwiecień",
    5: "maj",
    6: "czerwiec",
    7: "lipiec",
    8: "sierpień",
    9: "wrzesień",
    10: "październik",
    11: "listopad",
    12: "grudzień",
}


def parse_num(value) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def extract_inv_num(numer: str) -> str:
    match = re.search(r"FS\s+(\d+/D/\d+/\d+)", str(numer))
    if match:
        return match.group(1)
    return str(numer).replace("FS ", "").strip()


def load_b2b_invoices(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", names=COLS, skiprows=1)
    frame["inv_short"] = frame["Numer"].apply(extract_inv_num)
    frame["brutto_num"] = frame["Brutto"].apply(parse_num)
    frame["data_dt"] = pd.to_datetime(frame["Data"], format="%d-%m-%Y", errors="coerce")
    frame["has_nip"] = frame["NIP"].notna() & (frame["NIP"].astype(str).str.strip() != "")
    frame["has_vatin"] = frame["VATIN"].notna() & (frame["VATIN"].astype(str).str.strip() != "")

    filtered = frame[
        (frame["Kategoria"].astype(str).str.strip() == "Detal")
        & (frame["has_nip"] | frame["has_vatin"])
    ].copy()
    return filtered.sort_values(["data_dt", "inv_short"]).reset_index(drop=True)


def write_section(
    ws,
    header_row: int,
    title: str,
    amount_header: str,
    rows: pd.DataFrame,
    amount_col_name: str,
) -> int:
    header_fill = PatternFill("solid", fgColor="D9E1F2")
    bold = Font(bold=True)

    row = header_row
    if title:
        ws.cell(row, 1, title).font = bold
        row += 1
    header_row = row
    for col, label in enumerate(["L.P.", "Numer faktury", "Data wystawienia", amount_header], start=1):
        cell = ws.cell(header_row, col, label)
        cell.font = bold
        cell.fill = header_fill

    row_idx = header_row + 1
    total = 0.0
    for lp, (_, invoice) in enumerate(rows.iterrows(), start=1):
        ws.cell(row_idx, 1, lp)
        ws.cell(row_idx, 2, invoice["inv_short"])
        ws.cell(row_idx, 3, invoice["data_dt"].to_pydatetime())
        amount = invoice[amount_col_name]
        ws.cell(row_idx, 4, amount)
        total += float(amount)
        row_idx += 1

    ws.cell(row_idx, 3, "SUMA:").font = bold
    sum_cell = ws.cell(row_idx, 4, round(total, 2))
    sum_cell.font = bold
    return row_idx + 2


def build_workbook(month_label: str, pln: pd.DataFrame, eur: pd.DataFrame) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16

    ws.cell(1, 1, f"  DONNA - Sprzedaż B2B {month_label}").font = Font(bold=True)

    next_row = write_section(
        ws,
        2,
        "",
        "Kwota brutto PLN",
        pln,
        "brutto_num",
    )
    write_section(
        ws,
        next_row,
        "Faktury B2B w EURO",
        "Kwota brutto EUR",
        eur,
        "brutto_num",
    )
    return wb


def infer_output_path(csv_path: Path, frame: pd.DataFrame, explicit: Path | None) -> Path:
    if explicit:
        return explicit
    month_dt = frame["data_dt"].dropna().iloc[0]
    month_name = MONTH_PL[month_dt.month]
    number = month_dt.month
    return csv_path.parent / f"{number} zestawienie faktur b2b {month_name} {month_dt.year}.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args()

    b2b = load_b2b_invoices(args.csv)
    pln = b2b[b2b["Waluta"].astype(str).str.strip() == "PLN"].copy()
    eur = b2b[b2b["Waluta"].astype(str).str.strip() == "EUR"].copy()

    month_dt = b2b["data_dt"].dropna().iloc[0]
    month_label = f"{MONTH_PL[month_dt.month]} {month_dt.year}"

    out_path = infer_output_path(args.csv, b2b, args.output)
    wb = build_workbook(month_label, pln, eur)
    wb.save(out_path)

    print(f"Saved: {out_path}")
    print(f"PLN: {len(pln)} invoices, {pln['brutto_num'].sum():,.2f} PLN")
    print(f"EUR: {len(eur)} invoices, {eur['brutto_num'].sum():,.2f} EUR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
