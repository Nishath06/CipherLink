# stop_all.ps1
# Cleanly terminate CipherLink & Chat App services on ports 8000, 8001, 3000, 5173

$ports = @(8000, 8001, 3000, 5173)

Write-Host "Stopping any running services on ports 8000, 8001, 3000, 5173..." -ForegroundColor Yellow

foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            try {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "Stopping $($proc.ProcessName) (PID: $procId) on port $port..." -ForegroundColor Cyan
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            } catch {
                Write-Host "Could not stop PID $procId: $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "Port $port is free." -ForegroundColor DarkGray
    }
}

Write-Host "`nAll targeted services stopped." -ForegroundColor Green
