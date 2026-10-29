# Launch the drag-and-drop web UI, then open the browser.
Set-Location $PSScriptRoot
Start-Process "http://localhost:8080"
& .\.venv\Scripts\python.exe app.py
