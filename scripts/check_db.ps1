$ErrorActionPreference = 'Stop'
# Use explicit fallback so we don't boolean-evaluate the env var
if ($env:API_BASE -and $env:API_BASE.Trim() -ne '') { $apiBase = $env:API_BASE } else { $apiBase = 'http://localhost:8000' }
$key = $env:INTERNAL_KEY
$headers = @{}
if ($key) { $headers['X-Internal-Key'] = $key }

try {
    $resp = Invoke-RestMethod -Uri "$apiBase/internal/db-status" -Headers $headers -Method Get -ErrorAction Stop
} catch {
    Write-Error "Failed to call /internal/db-status: $_"
    exit 1
}

if (-not $resp.db_connected) {
    Write-Error "Database not connected: $($resp | ConvertTo-Json -Depth 3)"
    exit 1
}

$resp | ConvertTo-Json -Depth 3
