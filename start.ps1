# Nexus Dashboard — startup script (Windows PowerShell)
# Detects your local network IP automatically and starts Nexus.
# Usage: Right-click → Run with PowerShell, or: .\start.ps1

# ── Detect local IP ────────────────────────────────────────────
$HOST_IP = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object -Property InterfaceIndex |
    Select-Object -First 1).IPAddress

if (-not $HOST_IP) {
    $HOST_IP = "localhost"
    Write-Warning "Could not detect local IP, falling back to localhost."
    Write-Warning "Other devices on your network won't be able to reach the dashboard."
    Write-Warning "Set HOST_IP= manually in your .env file if needed."
    Write-Host ""
}

$env:HOST_IP = $HOST_IP

# ── Check .env exists ──────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Write-Error "No .env file found. Run: copy .env.example .env"
    Write-Error "Then open .env and set NEXUS_SECRET_KEY."
    exit 1
}

# ── Start ──────────────────────────────────────────────────────
Write-Host "Starting Nexus Dashboard..." -ForegroundColor Cyan
Write-Host ""

docker compose -f docker-compose-hub.yml up -d

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host " Nexus is running" -ForegroundColor Green
Write-Host ""
Write-Host " Dashboard  →  http://${HOST_IP}:3000" -ForegroundColor White
Write-Host " API        →  http://${HOST_IP}:8088" -ForegroundColor White
Write-Host " Excalidraw →  http://${HOST_IP}:3002" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "To stop:   docker compose -f docker-compose-hub.yml down"
Write-Host "To update: docker compose -f docker-compose-hub.yml pull; .\start.ps1"
