# ============================================
# TCP Environment Setup for CARLA 0.10.0 (PowerShell)
# ============================================

# Set CARLA root path
$env:CARLA_ROOT = "D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping"

# Set CARLA server executable
$env:CARLA_SERVER = "$env:CARLA_ROOT\CarlaUnreal.exe"

# Set TCP project root
$env:TCP_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

# Add CARLA Python API to PYTHONPATH
$carla_paths = @(
    "$env:CARLA_ROOT\PythonAPI",
    "$env:CARLA_ROOT\PythonAPI\carla",
    "$env:CARLA_ROOT\PythonAPI\carla\agents"
)

# Add TCP project paths to PYTHONPATH
$tcp_paths = @(
    $env:TCP_ROOT,
    "$env:TCP_ROOT\leaderboard",
    "$env:TCP_ROOT\leaderboard\team_code",
    "$env:TCP_ROOT\scenario_runner"
)

# Combine all paths
$all_paths = $carla_paths + $tcp_paths
$env:PYTHONPATH = ($all_paths -join ";")

# Set leaderboard root
$env:LEADERBOARD_ROOT = "$env:TCP_ROOT\leaderboard"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TCP Environment Variables Set:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "CARLA_ROOT: $env:CARLA_ROOT" -ForegroundColor Green
Write-Host "CARLA_SERVER: $env:CARLA_SERVER" -ForegroundColor Green
Write-Host "TCP_ROOT: $env:TCP_ROOT" -ForegroundColor Green
Write-Host "LEADERBOARD_ROOT: $env:LEADERBOARD_ROOT" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PYTHONPATH includes:" -ForegroundColor Yellow
foreach ($path in $all_paths) {
    Write-Host "  - $path" -ForegroundColor Gray
}
Write-Host "============================================" -ForegroundColor Cyan

