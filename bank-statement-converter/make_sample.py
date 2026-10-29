"""Generate a synthetic Wells Fargo-style statement PDF for testing."""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def money(v):
    return f"{v:,.2f}"


def build(path="samples/sample_statement.pdf"):
    c = canvas.Canvas(path, pagesize=letter)
    W, H = letter
    x_date, x_desc, x_dep, x_wd, x_bal = 50, 90, 380, 460, 545
    y = H - 60

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Wells Fargo"); y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Everyday Checking"); y -= 14
    c.drawString(50, y, "Account number: 1234567890"); y -= 14
    c.drawString(50, y, "Statement period: 10/01/2025 - 10/31/2025"); y -= 30

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Transaction history"); y -= 16
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_date, y, "Date")
    c.drawString(x_desc, y, "Check      Description")
    c.drawRightString(x_dep + 40, y, "Deposits/")
    c.drawRightString(x_wd + 40, y, "Withdrawals/")
    c.drawRightString(x_bal + 50, y, "Ending daily")
    y -= 11
    c.drawRightString(x_dep + 40, y, "Credits")
    c.drawRightString(x_wd + 40, y, "Debits")
    c.drawRightString(x_bal + 50, y, "balance")
    y -= 18
    c.setFont("Helvetica", 8)

    c.drawString(50, y, "Beginning balance on 10/1"); c.drawRightString(x_bal + 50, y, "5,000.00"); y -= 14

    txs = [
        ("10/2",  "eDeposit in branch/store 10/02/25 08:15:22 AM 123 Main St", 1500.00, None),
        ("10/3",  "Debit Card purchase on 10/02 at Grocery Store #402 San Jose CA", None, 82.45),
        ("10/6",  "Recurring Payment authorized on 10/05 Netflix.Com 866-579-7172 CA S454678", None, 15.99),
        ("10/8",  "Online Transfer to Savings xxxx4321 Ref #Ib03Klmtxp on 10/08/25", None, 500.00),
        ("10/10", "Payroll Deposit ACME CORP Payroll ID 99887", 2750.00, None),
        ("10/14", "Check 1056", None, 350.00),
        ("10/17", "ATM Withdrawal authorized on 10/16 ATM ID 2234 500 Market St San Francisco CA", None, 200.00),
        ("10/21", "Zelle From John Smith on 10/21 Ref #Rp09Qwerty", 125.00, None),
        ("10/27", "Online Payment to PG&E authorized on 10/26", None, 96.30),
    ]
    bal = 5000.00
    for date, desc, dep, wd in txs:
        bal += (dep or 0) - (wd or 0)
        c.drawString(x_date, y, date)
        c.drawString(x_desc, y, desc[:82])
        if dep: c.drawRightString(x_dep + 40, y, money(dep))
        if wd:  c.drawRightString(x_wd + 40, y, money(wd))
        c.drawRightString(x_bal + 50, y, money(bal))
        y -= 14
    y -= 6
    c.drawString(50, y, "Ending balance on 10/31"); c.drawRightString(x_bal + 50, y, money(bal)); y -= 24
    c.drawString(50, y, "Totals"); c.drawRightString(x_dep + 40, y, money(4375.00))
    c.drawRightString(x_wd + 40, y, money(1244.74))
    c.save()
    print(f"wrote {path}")


if __name__ == "__main__":
    build()
