# Create virtual environment and install requirements (avoids global uvicorn lock)
# Run from interview folder: .\setup_venv.ps1

$ErrorActionPreference = "Stop"
$venvDir = ".venv"

if (Test-Path $venvDir) {
    Write-Host "Virtual environment already exists at $venvDir"
} else {
    Write-Host "Creating virtual environment at $venvDir ..."
    python -m venv $venvDir
}

Write-Host "Activating and installing requirements..."
& "$venvDir\Scripts\pip.exe" install -r requirements.txt

Write-Host ""
Write-Host "Done. To run the server:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload"
Write-Host ""
Write-Host "Or in one line:"
Write-Host "  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload"
