# ============================================================================
# Visa Slot Tracker v3.2.4 — Smoke Test Wrapper
# ============================================================================
# Sets UTF-8 console encoding and invokes smoke_test.py.
# All test logic lives in smoke_test.py to avoid PowerShell↔Python quoting
# issues (the v3.2.3 smoke_test.ps1 had two parser bugs from this exact pain).
#
# Usage:   .\smoke_test.ps1
# Runtime: ~30 seconds
# ============================================================================

# UTF-8 console — required for emoji rendering in tracker output
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# Find Python interpreter
$python = "c:\python314\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        Write-Host ""
        Write-Host "FAIL: Python not found." -ForegroundColor Red
        Write-Host "Install Python 3.10+ from https://python.org and rerun." -ForegroundColor Yellow
        exit 1
    }
}

# Run the actual smoke test
& $python smoke_test.py
exit $LASTEXITCODE
