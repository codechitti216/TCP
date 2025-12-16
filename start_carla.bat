@echo off
REM ============================================
REM Start CARLA Server for TCP
REM ============================================

set "CARLA_ROOT=D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping"

echo Starting CARLA Server...
echo CARLA Path: %CARLA_ROOT%
echo.

REM Default port settings
set PORT=2000
if not "%1"=="" set PORT=%1

echo Using port: %PORT%
echo.

cd /d "%CARLA_ROOT%"

REM Start CARLA with specified settings
REM -carla-rpc-port: RPC port for client connections
REM -quality-level=Low: Use low quality for faster performance (change to Epic for better visuals)
REM -RenderOffScreen: Run without display window (remove if you want to see the simulation)

echo Starting CARLA...
echo Press Ctrl+C to stop the server.
echo.

CarlaUnreal.exe -carla-rpc-port=%PORT% -quality-level=Low

REM Alternative command with rendering window:
REM CarlaUnreal.exe -carla-rpc-port=%PORT% -quality-level=Epic -windowed -ResX=800 -ResY=600

