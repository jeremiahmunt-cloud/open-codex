# Wells Fargo Bank Statement → Excel Converter

A local, self-hosted equivalent of
[bankstatementtoexcelconverter.com/banks/us/wells-fargo](https://www.bankstatementtoexcelconverter.com/banks/us/wells-fargo).
Converts Wells Fargo PDF statements into **Excel (.xlsx), CSV, or JSON** — your
files never leave your machine.

## Features (mirroring the website)

- Extracts every transaction row: **date, check #, description,
  deposits/credits, withdrawals/debits, running balance**
- **Balance verification** — recomputes beginning balance + credits − debits
  and compares it to the statement's ending balance
- Exports **.xlsx** (Transactions + Summary sheets), **.csv**, or **.json**
- US format handling: MM/DD dates, comma-formatted dollar amounts
- Works with Wells Fargo **checking, savings, and business** statements that
  contain a *Transaction history* section
- **Drag-and-drop web UI** with transaction preview and flagged-row warnings
- No signup, no upload to third parties — runs entirely locally

## Document verification (`verifier.py`)

Every conversion also audits the PDF itself (disable with `--no-verify`):

| Category | What is checked |
|---|---|
| **Alignment** | Date/deposit/withdrawal/balance columns stay within 2.5–3 pt of their column centers — misaligned digits indicate manual editing |
| **Typography** | Every transaction line uses the same font face & size; deviations are flagged with page + line |
| **Fonts** | Font inventory per statement; non-embedded fonts (a re-editing artifact) are flagged |
| **Metadata** | Original PDF Producer/Creator/CreationDate preserved & reported; post-creation `ModDate` and consumer PDF editors (Acrobat, iLovePDF, …) are flagged |
| **Verbiage** | Core Wells Fargo wording (e.g. *Transaction history*, *Beginning balance on*) plus 10 phrases typical of business statements (*Monthly service fee summary*, *Account transaction fees summary*, *Primary account number*, …) |
| **Reconciliation** | ① beginning balance + credits − debits == ending balance ② per-row running-balance continuity ③ the statement's own *Totals* row vs computed sums ④ transaction count |

Results appear in the CLI output, a **Verification sheet** in the Excel export,
the `verification` block of the JSON export, and a **Document verification**
panel in the web UI.

## Windows — easiest way (no commands needed)

1. Install Python from https://www.python.org/downloads/ — **tick "Add python.exe to PATH"** on the first installer screen.
2. Open the `bank-statement-converter` folder.
3. **Double-click `START-HERE.bat`.**

That's it — it installs everything on first run, then opens the converter
in your browser at http://localhost:8080. Drag your PDF onto the page.

## Windows — PowerShell (manual)

```powershell
cd bank-statement-converter
powershell -ExecutionPolicy Bypass -File .\setup.ps1   # one-time setup
.\start-web.ps1                                        # web UI
.\convert.ps1 statement.pdf                            # or CLI -> .xlsx/.csv/.json
```

## Linux / macOS

```bash
cd bank-statement-converter
python3 -m venv .venv
.venv/bin/pip install pdfplumber pandas openpyxl flask reportlab
.venv/bin/python converter.py statement.pdf   # CLI
.venv/bin/python app.py                       # web UI at http://localhost:8080
```

## Generate a test statement

```bash
.venv/bin/python make_sample.py
.venv/bin/python converter.py samples/sample_statement.pdf
```

Expected output: 9 transactions, credits 4,375.00, debits 1,244.74,
balance verified (8,130.26).

## Notes & limitations

- **Scanned/image PDFs** have no text layer; run OCR first:
  `ocrmypdf in.pdf out.pdf` (the parser detects this and tells you).
- Credit-card statements use a different layout and are not yet supported.
- Always sanity-check the output against the original PDF before importing
  into accounting software; flagged rows are listed as warnings.
