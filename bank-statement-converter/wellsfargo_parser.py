"""Wells Fargo bank statement PDF parser.

Extracts transactions from Wells Fargo checking/savings statements using
positional (column-aware) text extraction via pdfplumber, mirroring the
behavior of bankstatementtoexcelconverter.com:

  - date, description, deposits/credits, withdrawals/debits, balance
  - beginning/ending balance + statement period detection
  - balance verification (beginning + credits - debits == ending)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

import pdfplumber

DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$")
AMOUNT_RE = re.compile(r"^-?\$?\d{1,3}(?:,\d{3})*\.\d{2}$")
BEGIN_BAL_RE = re.compile(r"Beginning balance on\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", re.I)
END_BAL_RE = re.compile(r"Ending balance on\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", re.I)
STMT_RE = re.compile(
    r"statement period[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:to|-|through)\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.I,
)

SKIP_LINE_PREFIXES = (
    "transaction history",
    "deposits/credits",
    "withdrawals/debits",
    "ending daily balance",
    "deposits and additions",
    "withdrawals and subtractions",
    "check number",
    "number date description",
)


@dataclass
class Transaction:
    date: str
    description: str
    check_number: Optional[str] = None
    deposit: Optional[float] = None
    withdrawal: Optional[float] = None
    balance: Optional[float] = None
    page: int = 0


@dataclass
class StatementResult:
    account_number: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    beginning_balance: Optional[float] = None
    ending_balance: Optional[float] = None
    transactions: list[Transaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_credits(self) -> float:
        return round(sum(t.deposit or 0 for t in self.transactions), 2)

    @property
    def total_debits(self) -> float:
        return round(sum(t.withdrawal or 0 for t in self.transactions), 2)

    def verify_balance(self) -> tuple[bool, str]:
        if self.beginning_balance is None or self.ending_balance is None:
            return False, "Beginning/ending balance not found; cannot verify."
        calc = round(self.beginning_balance + self.total_credits - self.total_debits, 2)
        if abs(calc - self.ending_balance) < 0.01:
            return True, f"Balance verified: {calc:,.2f} == {self.ending_balance:,.2f}"
        return False, (
            f"Balance mismatch: computed {calc:,.2f} vs statement ending "
            f"{self.ending_balance:,.2f} (diff {calc - self.ending_balance:+,.2f})"
        )

    def to_dict(self) -> dict:
        ok, msg = self.verify_balance()
        return {
            "account_number": self.account_number,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "beginning_balance": self.beginning_balance,
            "ending_balance": self.ending_balance,
            "total_credits": self.total_credits,
            "total_debits": self.total_debits,
            "balance_verified": ok,
            "verification_message": msg,
            "warnings": self.warnings,
            "transactions": [asdict(t) for t in self.transactions],
        }


def _parse_amount(text: str) -> Optional[float]:
    if AMOUNT_RE.match(text):
        return float(text.replace("$", "").replace(",", ""))
    return None


def _find_column_boundaries(page, tolerance: float = 3.0):
    """Locate x-positions of the Deposits/Credits, Withdrawals/Debits and
    Ending daily balance columns from the table header words."""
    words = page.extract_words()
    centers = {"deposit": [], "withdrawal": [], "balance": []}
    for i, w in enumerate(words):
        t = w["text"].lower()
        xc = (w["x0"] + w["x1"]) / 2
        if t in ("credits", "credits,"):
            centers["deposit"].append(xc)
        elif t in ("debits", "debits,"):
            centers["withdrawal"].append(xc)
        elif t == "balance" and i > 0 and words[i - 1]["text"].lower() == "daily":
            centers["balance"].append((w["x0"] + words[i - 1]["x1"]) / 2)
    if not all(centers.values()):
        return None
    dep = sum(centers["deposit"]) / len(centers["deposit"])
    wd = sum(centers["withdrawal"]) / len(centers["withdrawal"])
    bal = sum(centers["balance"]) / len(centers["balance"])
    if not (dep < wd < bal):
        return None
    mid1 = (dep + wd) / 2
    mid2 = (wd + bal) / 2
    return {"deposit_right": mid1, "withdrawal_right": mid2}


def _is_header_or_skip(text: str) -> bool:
    low = text.strip().lower()
    if not low:
        return True
    if low.startswith(SKIP_LINE_PREFIXES):
        return True
    if low in ("date", "check", "description", "credits", "debits"):
        return True
    return False


def parse_statement(pdf_path: str) -> StatementResult:
    result = StatementResult()
    in_tx_section = False
    current: Optional[Transaction] = None
    col_bounds = None

    def flush():
        nonlocal current
        if current is not None:
            current.description = re.sub(r"\s+", " ", current.description).strip()
            result.transactions.append(current)
            current = None

    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError("PDF has no pages (possibly encrypted or corrupt).")
        if pdf.pages[0].extract_text() is None:
            raise ValueError(
                "No extractable text found — this looks like a scanned/image PDF. "
                "Run OCR on it first (e.g. `ocrmypdf in.pdf out.pdf`)."
            )
        for page_no, page in enumerate(pdf.pages, start=1):
            if col_bounds is None:
                col_bounds = _find_column_boundaries(page)
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            # group words into visual lines by 'top' coordinate
            lines: dict[int, list[dict]] = {}
            for w in words:
                key = round(w["top"] / 3)
                lines.setdefault(key, []).append(w)

            for key in sorted(lines):
                ws = sorted(lines[key], key=lambda w: w["x0"])
                line_text = " ".join(w["text"] for w in ws)

                m = BEGIN_BAL_RE.search(line_text)
                if m:
                    for w in reversed(ws):
                        amt = _parse_amount(w["text"])
                        if amt is not None:
                            result.beginning_balance = amt
                            break
                    result.period_start = m.group(1)
                    continue
                m = END_BAL_RE.search(line_text)
                if m:
                    flush()
                    for w in reversed(ws):
                        amt = _parse_amount(w["text"])
                        if amt is not None:
                            result.ending_balance = amt
                            break
                    result.period_end = m.group(1)
                    in_tx_section = False
                    continue
                m = STMT_RE.search(line_text)
                if m:
                    result.period_start, result.period_end = m.group(1), m.group(2)

                if result.account_number is None:
                    am = re.search(r"[Aa]ccount\s*(?:number|#)?\s*[:\s]*([0-9]{6,})", line_text)
                    if am:
                        result.account_number = am.group(1)

                if "transaction history" in line_text.lower():
                    in_tx_section = True
                    continue

                if not in_tx_section:
                    continue
                if _is_header_or_skip(line_text):
                    continue
                # stop conditions: next section headers
                if re.match(r"^(summary of checks written|monthly service fee|interest\b|daily balance)", line_text.lower()):
                    flush()
                    in_tx_section = False
                    continue

                first = ws[0]["text"]
                if DATE_RE.match(first):
                    flush()
                    desc_words, amounts = [], []
                    check_number = None
                    for w in ws[1:]:
                        amt = _parse_amount(w["text"])
                        if amt is not None:
                            amounts.append((amt, (w["x0"] + w["x1"]) / 2))
                        elif re.fullmatch(r"\d{3,}", w["text"]) and check_number is None and not desc_words:
                            check_number = w["text"]
                        else:
                            desc_words.append(w["text"])
                    current = Transaction(date=first, description=" ".join(desc_words),
                                          check_number=check_number, page=page_no)
                    _assign_amounts(current, amounts, col_bounds)
                elif current is not None and not AMOUNT_RE.match(first):
                    # continuation of a multi-line description
                    extra = [w["text"] for w in ws if _parse_amount(w["text"]) is None]
                    if extra:
                        current.description += " " + " ".join(extra)
    flush()

    if not result.transactions:
        result.warnings.append(
            "No transactions found. Verify this is a Wells Fargo checking/savings "
            "statement with a 'Transaction history' section."
        )
    # de-duplicate continuation artifacts
    for t in result.transactions:
        if t.deposit is not None and t.withdrawal is not None:
            result.warnings.append(
                f"Row {t.date} '{t.description[:40]}' has both a credit and a debit — review manually."
            )
    return result


def _assign_amounts(tx: Transaction, amounts: list[tuple[float, float]], col_bounds):
    """Classify amount columns. Rightmost amount on a transaction line is the
    running balance; the other is credit or debit by x-position (or keyword)."""
    if not amounts:
        tx.balance = None
        return
    amounts_sorted = sorted(amounts, key=lambda a: a[1])
    if len(amounts_sorted) >= 2:
        tx.balance = amounts_sorted[-1][0]
        amt, xc = amounts_sorted[0]
    else:
        amt, xc = amounts_sorted[0]
        tx.balance = None

    if col_bounds is not None:
        if xc < col_bounds["deposit_right"]:
            tx.deposit = amt
        else:
            tx.withdrawal = amt
    else:
        # fallback: keyword heuristic
        desc = tx.description.lower()
        credit_kw = ("deposit", "credit", "transfer from", "refund", "interest paid",
                     "zelle from", "wire trans svc charge", "mobile deposit")
        tx.deposit = amt if any(k in desc for k in credit_kw) else None
        tx.withdrawal = None if tx.deposit is not None else amt
