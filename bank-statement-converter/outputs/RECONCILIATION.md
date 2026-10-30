# Statement reconciliation — account 2893191219

Checked against the uploaded PDFs on 2026-10-30. Figures are the statement's own summary row, not a second source.

| Month | Status | Beginning | Credits | Debits | Ending |
|---|---|---:|---:|---:|---:|
| June 2026 | Not processed — upload is an iCloud placeholder, not a PDF | — | — | — | — |
| July 2026 | Reconciled | 2,297.43 | 41,787.94 | 41,681.11 | 2,404.26 |
| August 2026 | Not uploaded | — | — | — | — |
| September 2026 | Reconciled except a $0.01 residual | 236.59 | 128,954.17 printed / 128,954.18 computed | 103,495.16 | 25,695.60 printed / 25,695.61 computed |

July identity: 2,297.43 + 41,787.94 − 41,681.11 = 2,404.26.

September identity on the statement: 236.59 + 128,954.17 − 103,495.16 = 25,695.60.

July's ending balance (2,404.26) does not roll into September's beginning balance (236.59). August is not in `uploads/`, so that $2,167.67 gap cannot be reconciled from these files.

## September adjustments

The first OCR pass was short $271.63 of debits and did not match the printed totals. Each correction below was read from the statement image. Debits now match the printed total of 103,495.16 exactly.

| What was wrong | Correction | Debit change |
|---|---|---:|
| 9/4 Barry's Ace — description only, no amount (page 2) | Debit 7.45 | +7.45 |
| 9/4 Klarna*Airbnb — description only, no amount (page 2) | Debit 53.72 | +53.72 |
| 9/11 Lowes read as 249.00; the next row was swallowed (page 5) | Lowes is 117.75. Inserted Financelobby recurring payment 249.00 | +117.75 |
| 9/17 three Apple Cash transfers merged into one 10.00 row (page 8) | 50.00, 20.00, and 10.00 | +70.00 |
| 9/22 Homedepot.Com — description only, no amount (page 9) | Debit 22.71 | +22.71 |
| Page-header text (`September 30, 2026 … Page N of 14`) copied into descriptions | Stripped. Amounts unchanged | 0.00 |
| Several 9/17 rows dated 9/7 | Date corrected to 9/17 | 0.00 |

7.45 + 53.72 + 117.75 + 70.00 + 22.71 = 271.63.

After those corrections, every printed daily balance through 9/29 (26,633.93) matches the running sum. No transaction row is still missing an amount.

## The remaining $0.01

Credits computed from the rows are 128,954.18. The statement prints 128,954.17. The same cent shows up in the ending balance: rows after the 9/29 daily balance of 26,633.93 sum to 25,695.61, and the statement prints 25,695.60.

The non-round amounts on pages 10–11 (37.48, 31.65, 78.68, 90.80, interest 0.29) and the large credits (95,681.31, 28,089.00, 2,932.50, 2,112.90) match the images. Nothing was plugged to force the last cent. The register is otherwise reconciled to the printed debit total and to the daily-balance column.
