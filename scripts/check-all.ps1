# One command to check your work before opening a PR (see PIPELINE_README.md).
# Usage: .\scripts\check-all.ps1 [--fix] [--no-ai] [--base origin/main]
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$py = if (Test-Path '.venv\Scripts\python.exe') { '.venv\Scripts\python.exe' } else { 'py' }
& $py -m gate all @args
exit $LASTEXITCODE
