# start_all.ps1
# Launch CipherLink & Chat App projects locally without Docker

$projectRoot = $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Starting CipherLink & Chat App Services " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. CipherLink Backend (Port 8001)
Write-Host "[1/4] Launching CipherLink Backend on http://localhost:8001..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\cipherlink\backend'; `$host.UI.RawUI.WindowTitle = 'CipherLink Backend (:8001)'; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"

# 2. CipherLink Frontend (Port 5173)
Write-Host "[2/4] Launching CipherLink Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\cipherlink\frontend'; `$host.UI.RawUI.WindowTitle = 'CipherLink Frontend (:5173)'; npm run dev"

# 3. Chat App Backend (Port 8000)
Write-Host "[3/4] Launching Chat App Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\chat_app\backend'; `$host.UI.RawUI.WindowTitle = 'Chat App Backend (:8000)'; .\env\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

# 4. Chat App Frontend (Port 3000)
Write-Host "[4/4] Launching Chat App Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\chat_app\frontend'; `$host.UI.RawUI.WindowTitle = 'Chat App Frontend (:3000)'; npm run dev"

Write-Host "`nAll 4 services launched successfully!" -ForegroundColor Cyan
Write-Host "---------------------------------------------------------" -ForegroundColor DarkGray
Write-Host " CipherLink Web Dashboard : http://localhost:5173" -ForegroundColor White
Write-Host " CipherLink Swagger Docs  : http://localhost:8001/docs" -ForegroundColor White
Write-Host " Chat App Web Interface   : http://localhost:3000" -ForegroundColor White
Write-Host " Chat App Swagger Docs    : http://localhost:8000/docs" -ForegroundColor White
Write-Host "---------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Run .\stop_all.ps1 to stop all 4 services." -ForegroundColor Yellow
