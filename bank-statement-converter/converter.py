"""Convert parsed Wells Fargo statements to Excel / CSV / JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from wellsfargo_parser import StatementResult, parse_statement
from verifier import VerificationReport, verify_document

COLUMNS = ["Date", "Check #", "Description", "Deposits/Credits",
           "Withdrawals/Debits", "Balance", "Page"]


def result_to_dataframe(result: StatementResult) -> pd.DataFrame:
    rows = [{
        "Date": t.date,
        "Check #": t.check_number or "",
        "Description": t.description,
        "Deposits/Credits": t.deposit,
        "Withdrawals/Debits": t.withdrawal,
        "Balance": t.balance,
        "Page": t.page,
    } for t in result.transactions]
    return pd.DataFrame(rows, columns=COLUMNS)


def _summary_frame(result: StatementResult) -> pd.DataFrame:
    ok, msg = result.verify_balance()
    data = [
        ("Account number", result.account_number or ""),
        ("Period start", result.period_start or ""),
        ("Period end", result.period_end or ""),
        ("Beginning balance", result.beginning_balance),
        ("Ending balance", result.ending_balance),
        ("Total credits", result.total_credits),
        ("Total debits", result.total_debits),
        ("Transactions", len(result.transactions)),
        ("Balance verified", "YES" if ok else "NO"),
        ("Verification", msg),
    ]
    for w in result.warnings:
        data.append(("Warning", w))
    return pd.DataFrame(data, columns=["Field", "Value"])


def convert(pdf_path: str, out_path: str, fmt: str | None = None,
            verify: bool = True) -> tuple[StatementResult, "VerificationReport | None"]:
    """Parse `pdf_path` and write the result to `out_path`.

    Format is inferred from the output extension (.xlsx/.csv/.json) unless
    `fmt` is given. Excel output contains Transactions + Summary (+ Verification)
    sheets. Returns (parse_result, verification_report_or_None).
    """
    result = parse_statement(pdf_path)
    report = verify_document(pdf_path, result) if verify else None
    out = Path(out_path)
    fmt = (fmt or out.suffix.lstrip(".")).lower()

    if fmt in ("xlsx", "excel"):
        tx = result_to_dataframe(result)
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            tx.to_excel(writer, sheet_name="Transactions", index=False)
            _summary_frame(result).to_excel(writer, sheet_name="Summary", index=False)
            if report is not None:
                rows = [{"Category": c.category, "Check": c.name,
                         "Status": c.status.upper(), "Detail": c.detail}
                        for c in report.checks]
                pd.DataFrame(rows).to_excel(writer, sheet_name="Verification", index=False)
                vws = writer.sheets["Verification"]
                for col, width in zip("ABCD", (15, 26, 9, 100)):
                    vws.column_dimensions[col].width = width
            ws = writer.sheets["Transactions"]
            for col, width in zip("ABCDEFG", (10, 9, 70, 16, 18, 14, 6)):
                ws.column_dimensions[col].width = width
            for col in ("D", "E", "F"):
                for row in range(2, len(tx) + 2):
                    ws[f"{col}{row}"].number_format = '#,##0.00'
    elif fmt == "csv":
        result_to_dataframe(result).to_csv(out, index=False)
    elif fmt == "json":
        payload = result.to_dict()
        if report is not None:
            payload["verification"] = report.to_dict()
        out.write_text(json.dumps(payload, indent=2))
    else:
        raise ValueError(f"Unsupported format '{fmt}'. Use xlsx, csv or json.")
    return result, report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Convert a Wells Fargo bank statement PDF to Excel/CSV/JSON.")
    ap.add_argument("pdf", help="Path to the Wells Fargo statement PDF")
    ap.add_argument("-o", "--output", help="Output file (.xlsx/.csv/.json). "
                    "Defaults to <pdf-stem>.xlsx")
    ap.add_argument("-f", "--format", choices=["xlsx", "csv", "json"],
                    help="Output format (overrides extension)")
    ap.add_argument("--no-verify", action="store_true",
                    help="Skip document verification checks")
    args = ap.parse_args()

    out_path = args.output or str(Path(args.pdf).with_suffix(".xlsx"))
    res, report = convert(args.pdf, out_path, args.format, verify=not args.no_verify)
    ok, msg = res.verify_balance()
    print(f"Extracted {len(res.transactions)} transactions -> {out_path}")
    print(f"Credits: {res.total_credits:,.2f} | Debits: {res.total_debits:,.2f}")
    print(("✔ " if ok else "✘ ") + msg)
    for w in res.warnings:
        print("⚠ " + w)
    if report is not None:
        p, w_, f = report.score
        print(f"\nVerification: {p} passed, {w_} warning(s), {f} failed")
        icons = {"pass": "✔", "warn": "⚠", "fail": "✘"}
        for c in report.checks:
            print(f"  {icons[c.status]} [{c.category}] {c.name}: {c.detail}")
        if report.fonts:
            print("  Fonts: " + ", ".join(report.fonts))
