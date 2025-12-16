@echo off
REM ============================================
REM Test CARLA Connection
REM ============================================

REM Load environment variables
call "%~dp0set_env.bat"

echo.
echo Testing CARLA connection...
echo.

cd /d "%TCP_ROOT%"

python test_carla_connection.py %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Connection test PASSED!
) else (
    echo.
    echo Connection test FAILED!
    echo.
    echo Make sure:
    echo   1. CARLA server is running (run start_carla.bat)
    echo   2. CARLA Python package is installed (run install_carla.bat)
)

pause

