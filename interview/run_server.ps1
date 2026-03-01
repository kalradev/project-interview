# Run the interview API server using the virtual environment (no global uvicorn needed)
# Run from interview folder: .\run_server.ps1

$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Run first: .\setup_venv.ps1"
    exit 1
}
& $venvPython -m uvicorn app.main:app --reload
