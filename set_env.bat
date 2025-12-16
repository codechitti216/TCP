@echo off
REM ============================================
REM TCP Environment Setup for CARLA 0.9.10
REM ============================================

REM Set CARLA root path (adjust if needed)
set "CARLA_ROOT=D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping"

REM Set CARLA server executable
set "CARLA_SERVER=%CARLA_ROOT%\CarlaUnreal.exe"

REM Set TCP project root (current directory)
set "TCP_ROOT=%~dp0"

REM Add CARLA Python API to PYTHONPATH
set "PYTHONPATH=%PYTHONPATH%;%CARLA_ROOT%\PythonAPI"
set "PYTHONPATH=%PYTHONPATH%;%CARLA_ROOT%\PythonAPI\carla"
set "PYTHONPATH=%PYTHONPATH%;%CARLA_ROOT%\PythonAPI\carla\agents"

REM Add TCP project paths to PYTHONPATH
set "PYTHONPATH=%PYTHONPATH%;%TCP_ROOT%"
set "PYTHONPATH=%PYTHONPATH%;%TCP_ROOT%leaderboard"
set "PYTHONPATH=%PYTHONPATH%;%TCP_ROOT%leaderboard\team_code"
set "PYTHONPATH=%PYTHONPATH%;%TCP_ROOT%scenario_runner"

REM Set leaderboard root
set "LEADERBOARD_ROOT=%TCP_ROOT%leaderboard"

echo ============================================
echo TCP Environment Variables Set:
echo ============================================
echo CARLA_ROOT=%CARLA_ROOT%
echo CARLA_SERVER=%CARLA_SERVER%
echo TCP_ROOT=%TCP_ROOT%
echo LEADERBOARD_ROOT=%LEADERBOARD_ROOT%
echo ============================================
echo.
echo PYTHONPATH includes:
echo   - CARLA PythonAPI
echo   - TCP project paths
echo ============================================

