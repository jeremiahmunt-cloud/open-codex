# Convert a statement PDF from the command line.
# Usage:  .\convert.ps1 statement.pdf            -> Excel (default)
#         .\convert.ps1 statement.pdf out.csv    -> CSV
#         .\convert.ps1 statement.pdf out.json   -> JSON
param(
    [Parameter(Mandatory=$true)][string]$Pdf,
    [string]$Out = ""
)
Set-Location $PSScriptRoot
if ($Out) {
    & .\.venv\Scripts\python.exe converter.py $Pdf -o $Out
} else {
    & .\.venv\Scripts\python.exe converter.py $Pdf
}
