# June 2026 statement — still not processed

Re-checked `uploads/Wells Fargo June _6010.pdf` on 2026-10-30. It is still not a PDF.

- Size: 3,672 bytes (a real statement in this set is 1–10 MB).
- Format: Apple binary property list (`bplist00` / `NSKeyedArchiver`), an iCloud Drive file-provider placeholder.
- Display name inside the plist: `Wells Fargo June .pdf` (`com.adobe.pdf`).
- No PDF header, no page stream, and no embedded document bytes. There is nothing to OCR, parse, or reconcile.

July and September were adjusted and reconciled. See `RECONCILIATION.md`.

To process June: in the Wells Fargo app or wellsfargo.com, open Statements & Documents, use the download icon (not the iOS share sheet), and upload that PDF into `uploads/`. A real June PDF will start with `%PDF` and will be much larger than a few kilobytes.
