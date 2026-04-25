Write-Host "boran-ai başlatılıyor..."

# backend (0.0.0.0 to allow Android emulator/device access)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$PSScriptRoot`"; .\.venv\Scripts\activate; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

# frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$PSScriptRoot\frontend`"; npm run dev -- --host 127.0.0.1 --port 5173"

Write-Host "backend -> http://0.0.0.0:8000 (host)"
Write-Host "frontend -> http://127.0.0.1:5173"
