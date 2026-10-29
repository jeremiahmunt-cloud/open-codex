"""Document verification for Wells Fargo statement PDFs.

Runs authenticity/consistency checks beyond plain extraction:

  1. Alignment      — date/amount columns line up on consistent x-positions
                      (misaligned digits are a classic tamper indicator)
  2. Typography     — uniform font family/size inside the transaction table;
                      flags lines set in a different face or size
  3. Fonts          — inventory of fonts used and whether they are embedded
  4. Metadata       — original PDF metadata (producer, creator, creation/
                      modification dates); flags post-creation modification
  5. Verbiage       — expected Wells Fargo wording present on the statement
  6. Reconciliation — beginning balance + credits − debits == ending balance,
                      per-row running-balance continuity, and the statement's
                      own "Totals" row cross-checked against computed sums

Each check returns (status, detail) with status in {"pass", "warn", "fail"}.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

import pdfplumber

from wellsfargo_parser import (
    DATE_RE,
    BEGIN_BAL_RE,
    END_BAL_RE,
    StatementResult,
    _find_column_boundaries,
    _parse_amount,
)

AMOUNT_COL_TOL = 3.0   # points of x-drift tolerated in amount columns
DATE_COL_TOL = 2.5     # points of x-drift tolerated in the date column

# Wells Fargo statement wording. "core" phrases should nearly always be there;
# "business" phrases are typical of business/complete statements.
# NB: Wells Fargo headers wrap across two lines ("Deposits/" over "Credits"),
# so phrases must match tokens that survive line collapsing.
CORE_PHRASES = [
    "wells fargo",
    "transaction history",
    "beginning balance on",
    "ending balance on",
    "ending daily",
    "account number",
]
BUSINESS_PHRASES = [
    "deposits/",
    "withdrawals/",
    "monthly service fee summary",
    "account transaction fees summary",
    "primary account number",
    "important account information",
    "summary of checks written",
    "daily balance summary",
    "wells fargo bank, n.a.",
    "questions?",
]

# PDF producers/editors that indicate the file was re-saved after generation.
EDITOR_HINTS = ("acrobat", "ilovepdf", "smallpdf", "pdfescape", "nitro",
                "foxit", "photoshop", "gimp", "preview", "word", "canva")


@dataclass
class Check:
    category: str
    name: str
    status: str          # pass | warn | fail
    detail: str


@dataclass
class VerificationReport:
    checks: list[Check] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add(self, category: str, name: str, status: str, detail: str):
        self.checks.append(Check(category, name, status, detail))

    @property
    def score(self) -> tuple[int, int, int]:
        """(passes, warnings, failures)"""
        return (
            sum(c.status == "pass" for c in self.checks),
            sum(c.status == "warn" for c in self.checks),
            sum(c.status == "fail" for c in self.checks),
        )

    def to_dict(self) -> dict:
        p, w, f = self.score
        return {
            "summary": {"pass": p, "warn": w, "fail": f},
            "fonts": self.fonts,
            "metadata": self.metadata,
            "checks": [asdict(c) for c in self.checks],
        }


# ---------------------------------------------------------------- extraction

def _tx_lines(page):
    """Rebuild visual lines of the transaction table as (text, words) tuples."""
    words = page.extract_words(keep_blank_chars=False)
    lines: dict[int, list[dict]] = {}
    for w in words:
        lines.setdefault(round(w["top"] / 3), []).append(w)
    out = []
    for key in sorted(lines):
        ws = sorted(lines[key], key=lambda w: w["x0"])
        out.append((" ".join(w["text"] for w in ws), ws))
    return out


def _tx_rows(page):
    """Yield (line_text, words) for lines that start a transaction row."""
    for text, ws in _tx_lines(page):
        if ws and DATE_RE.match(ws[0]["text"]) and not BEGIN_BAL_RE.search(text) \
                and not END_BAL_RE.search(text):
            yield text, ws


# ------------------------------------------------------------------- checks

def _split_columns(values, min_gap: float = 30.0):
    """Split (x, page, text) tuples into column clusters by x-position gaps."""
    if not values:
        return []
    values = sorted(values, key=lambda v: v[0])
    clusters, cur = [[values[0]]], values[0][0]
    for v in values[1:]:
        if v[0] - cur > min_gap:
            clusters.append([v])
        else:
            clusters[-1].append(v)
        cur = v[0]
    return clusters


def check_alignment(report: VerificationReport, pages, col_bounds):
    date_x0, bal_xs, amt_xs = [], [], []
    for page in pages:
        for text, ws in _tx_rows(page):
            date_x0.append((round(ws[0]["x0"], 1), page.page_number, ws[0]["text"]))
            amounts = [(w, _parse_amount(w["text"])) for w in ws[1:]]
            amounts = [(w, a) for w, a in amounts if a is not None]
            if not amounts:
                continue
            bal_w = max(amounts, key=lambda t: t[0]["x1"])[0]
            bal_xs.append((round((bal_w["x0"] + bal_w["x1"]) / 2, 1), page.page_number, bal_w["text"]))
            for w, _ in amounts:
                if w is not bal_w:
                    amt_xs.append((round((w["x0"] + w["x1"]) / 2, 1), page.page_number, w["text"]))

    def outliers_in(values, tol):
        if len(values) < 2:
            return [], 0.0
        center = sum(v[0] for v in values) / len(values)
        return [v for v in values if abs(v[0] - center) > tol], center

    problems = []
    # deposits and withdrawals are separate columns — cluster them apart
    groups = [("date", [date_x0], DATE_COL_TOL), ("balance", [bal_xs], AMOUNT_COL_TOL)]
    amt_clusters = _split_columns(amt_xs)
    if len(amt_clusters) == 1:
        groups.append(("amount", amt_clusters, AMOUNT_COL_TOL))
    else:
        labels = ["deposit", "withdrawal"][:len(amt_clusters)] or ["amount"]
        groups.append((("deposit/withdrawal"), amt_clusters, AMOUNT_COL_TOL))
    for label, clusters, tol in groups:
        for cl in clusters:
            outs, center = outliers_in(cl, tol)
            for x, pg, txt in outs:
                problems.append(f"{label} '{txt}' p{pg} at x={x} "
                                f"(column center {center:.1f})")
    if problems:
        report.add("Alignment", "Column alignment", "fail",
                   f"{len(problems)} misaligned value(s): " + "; ".join(problems[:6])
                   + (" …" if len(problems) > 6 else ""))
    else:
        n = len(date_x0)
        report.add("Alignment", "Column alignment", "pass",
                   f"All {n} transaction rows align within tolerance "
                   f"(date ≤{DATE_COL_TOL}pt, amounts ≤{AMOUNT_COL_TOL}pt).")


def check_typography(report: VerificationReport, pages):
    from collections import Counter
    styles: dict[tuple, int] = Counter()
    per_line: list[dict] = []
    for page in pages:
        chars = page.chars
        if not chars:
            continue
        lines: dict[int, list[dict]] = {}
        for ch in chars:
            lines.setdefault(round(ch["top"] / 3), []).append(ch)
        for key, chs in sorted(lines.items()):
            text = "".join(c["text"] for c in sorted(chs, key=lambda c: c["x0"]))
            if not re.match(r"^\s*\d{1,2}/\d{1,2}(?!\d)", text):
                continue
            line_styles = Counter((c["fontname"], round(c["size"], 1)) for c in chs)
            for st, n in line_styles.items():
                styles[st] += n
            per_line.append({"text": text.strip()[:40], "styles": dict(line_styles),
                             "page": page.page_number})
    if not styles:
        report.add("Typography", "Font consistency", "warn",
                   "No character data available (scanned PDF?).")
        return
    dominant = max(styles, key=styles.get)
    odd = [l for l in per_line
           if any(st != dominant for st in l["styles"])]
    report.fonts = sorted({f for f, _ in styles})
    if odd:
        examples = "; ".join(f"p{l['page']} '{l['text']}'" for l in odd[:5])
        report.add("Typography", "Font consistency", "fail",
                   f"{len(odd)}/{len(per_line)} transaction lines deviate from the "
                   f"dominant style {dominant}: {examples}")
    else:
        report.add("Typography", "Font consistency", "pass",
                   f"All {len(per_line)} transaction lines use {dominant[0]} "
                   f"{dominant[1]}pt uniformly.")


def check_metadata(report: VerificationReport, pdf):
    md = dict(pdf.metadata or {})
    report.metadata = {k: str(v) for k, v in md.items() if v}
    created = md.get("CreationDate")
    modded = md.get("ModDate")
    producer = str(md.get("Producer", ""))
    creator = str(md.get("Creator", ""))
    tool = f"{producer} {creator}".lower()

    if not md:
        report.add("Metadata", "PDF metadata", "warn",
                   "No metadata present — cannot confirm original generation.")
    else:
        report.add("Metadata", "PDF metadata", "pass",
                   f"Producer: {producer or '—'} | Creator: {creator or '—'} | "
                   f"Created: {created or '—'}")

    if modded and created and str(modded) != str(created):
        report.add("Metadata", "Modification history", "warn",
                   f"File modified after creation (ModDate {modded} ≠ CreationDate {created}).")
    elif modded:
        report.add("Metadata", "Modification history", "pass",
                   "No post-creation modification recorded.")
    if any(h in tool for h in EDITOR_HINTS):
        report.add("Metadata", "Generator tool", "warn",
                   f"Produced/edited with a consumer PDF tool ('{producer or creator}') "
                   "rather than a bank system.")
    # embedded-font check: non-embedded fonts often appear after re-editing
    try:
        non_embedded = [f for f in pdf.pages[0].fonts
                        if not f.get("FontDescriptor")]
        if non_embedded:
            report.add("Fonts", "Font embedding", "warn",
                       f"{len(non_embedded)} font(s) not embedded: "
                       + ", ".join(f.get("BaseFont", "?") for f in non_embedded[:5]))
        else:
            report.add("Fonts", "Font embedding", "pass", "All fonts embedded.")
    except Exception:
        pass


def check_verbiage(report: VerificationReport, full_text: str):
    text = re.sub(r"\s+", " ", full_text.lower())
    core_missing = [p for p in CORE_PHRASES if p not in text]
    biz_found = [p for p in BUSINESS_PHRASES if p in text]
    biz_missing = [p for p in BUSINESS_PHRASES if p not in text]

    if len(core_missing) >= len(CORE_PHRASES) // 2 + 1:
        report.add("Verbiage", "Core Wells Fargo wording", "fail",
                   "Missing expected phrases: " + ", ".join(f"'{p}'" for p in core_missing))
    elif core_missing:
        report.add("Verbiage", "Core Wells Fargo wording", "warn",
                   "Missing: " + ", ".join(f"'{p}'" for p in core_missing))
    else:
        report.add("Verbiage", "Core Wells Fargo wording", "pass",
                   f"All {len(CORE_PHRASES)} core phrases present.")

    if biz_missing:
        report.add("Verbiage", "Business-statement wording", "warn",
                   f"Found {len(biz_found)}/{len(BUSINESS_PHRASES)} typical business "
                   f"phrases. Not found: " + ", ".join(f"'{p}'" for p in biz_missing[:5])
                   + (" …" if len(biz_missing) > 5 else ""))
    else:
        report.add("Verbiage", "Business-statement wording", "pass",
                   f"All {len(BUSINESS_PHRASES)} typical business phrases present.")


def check_reconciliation(report: VerificationReport, result: StatementResult,
                         full_text: str):
    # 1. overall math
    ok, msg = result.verify_balance()
    report.add("Reconciliation", "Overall balance", "pass" if ok else "fail", msg)

    # 2. per-row running-balance continuity
    if result.beginning_balance is None:
        report.add("Reconciliation", "Running balances", "warn",
                   "Beginning balance unknown — cannot check per-row continuity.")
    else:
        expected = result.beginning_balance
        broken = []
        checked = 0
        for i, t in enumerate(result.transactions, 1):
            expected = round(expected + (t.deposit or 0) - (t.withdrawal or 0), 2)
            if t.balance is None:
                continue
            checked += 1
            if abs(t.balance - expected) >= 0.01:
                broken.append(f"row {i} ({t.date}): stated {t.balance:,.2f}, "
                              f"computed {expected:,.2f}")
        if broken:
            report.add("Reconciliation", "Running balances", "fail",
                       f"{len(broken)} break(s): " + "; ".join(broken[:5])
                       + (" …" if len(broken) > 5 else ""))
        elif checked:
            report.add("Reconciliation", "Running balances", "pass",
                       f"Running balance continuous across all {checked} rows.")

    # 3. statement's own Totals row vs computed sums
    m = re.search(r"^Totals\b(.*)$", full_text, re.M | re.I)
    if m:
        amounts = re.findall(r"\$?(\d{1,3}(?:,\d{3})*\.\d{2})", m.group(1))
        vals = [float(a.replace(",", "")) for a in amounts]
        if len(vals) >= 2:
            dep_ok = abs(vals[0] - result.total_credits) < 0.01
            wd_ok = abs(vals[1] - result.total_debits) < 0.01
            if dep_ok and wd_ok:
                report.add("Reconciliation", "Statement totals row", "pass",
                           f"Totals row matches computed sums "
                           f"(credits {vals[0]:,.2f}, debits {vals[1]:,.2f}).")
            else:
                report.add("Reconciliation", "Statement totals row", "fail",
                           f"Totals row {vals[:2]} vs computed "
                           f"credits {result.total_credits:,.2f} / "
                           f"debits {result.total_debits:,.2f}.")

    # 4. sanity: nonzero activity
    if not result.transactions:
        report.add("Reconciliation", "Transaction count", "fail",
                   "No transactions extracted.")
    else:
        report.add("Reconciliation", "Transaction count", "pass",
                   f"{len(result.transactions)} transactions extracted.")


# -------------------------------------------------------------------- entry

def verify_document(pdf_path: str, result: Optional[StatementResult] = None
                    ) -> VerificationReport:
    if result is None:
        from wellsfargo_parser import parse_statement
        result = parse_statement(pdf_path)
    report = VerificationReport()
    with pdfplumber.open(pdf_path) as pdf:
        pages = list(pdf.pages)
        col_bounds = None
        for p in pages:
            col_bounds = _find_column_boundaries(p)
            if col_bounds:
                break
        full_text = "\n".join(p.extract_text() or "" for p in pages)
        check_metadata(report, pdf)
        check_alignment(report, pages, col_bounds)
        check_typography(report, pages)
    check_verbiage(report, full_text)
    check_reconciliation(report, result, full_text)
    return report
