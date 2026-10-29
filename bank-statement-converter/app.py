"""Local web UI mimicking bankstatementtoexcelconverter.com:
drag-and-drop a Wells Fargo PDF, preview transactions, download Excel/CSV/JSON."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from converter import convert

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB uploads
WORK_DIR = Path(tempfile.gettempdir()) / "wf-converter"
WORK_DIR.mkdir(exist_ok=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/convert")
def api_convert():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a PDF file."}), 400
    job = WORK_DIR / uuid.uuid4().hex
    job.mkdir()
    pdf_path = job / "statement.pdf"
    f.save(pdf_path)
    try:
        result, report = convert(str(pdf_path), str(job / "statement.xlsx"))
        convert(str(pdf_path), str(job / "statement.csv"), "csv", verify=False)
        convert(str(pdf_path), str(job / "statement.json"), "json")
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    ok, msg = result.verify_balance()
    return jsonify({
        "job": job.name,
        "summary": {
            "account_number": result.account_number,
            "period_start": result.period_start,
            "period_end": result.period_end,
            "beginning_balance": result.beginning_balance,
            "ending_balance": result.ending_balance,
            "total_credits": result.total_credits,
            "total_debits": result.total_debits,
            "count": len(result.transactions),
            "verified": ok,
            "verification_message": msg,
            "warnings": result.warnings,
            "verification": report.to_dict() if report else None,
        },
        "preview": [
            {"date": t.date, "check": t.check_number or "", "description": t.description,
             "deposit": t.deposit, "withdrawal": t.withdrawal, "balance": t.balance}
            for t in result.transactions[:50]
        ],
    })


@app.get("/api/download/<job>/<fmt>")
def download(job: str, fmt: str):
    if fmt not in ("xlsx", "csv", "json") or not job.isalnum():
        return jsonify({"error": "Invalid request"}), 400
    path = WORK_DIR / job / f"statement.{fmt}"
    if not path.exists():
        return jsonify({"error": "Job expired — convert again."}), 404
    return send_file(path, as_attachment=True,
                     download_name=f"wells-fargo-statement.{fmt}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
