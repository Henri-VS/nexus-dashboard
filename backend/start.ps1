Write-Host "Starting Nexus..." -ForegroundColor Green

# Start backend in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\venv\Scripts\activate; python run.py" -WindowStyle Normal

# Wait for backend to start
Start-Sleep -Seconds 3

# Start frontend in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\frontend'; npm run dev" -WindowStyle Normal

Write-Host "Nexus starting..." -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8088" -ForegroundColor Cyan
Write-Host "API docs: http://localhost:8088/docs" -ForegroundColor Cyan
