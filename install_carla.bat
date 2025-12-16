@echo off
REM ============================================
REM Install CARLA Python Package
REM ============================================

set "CARLA_ROOT=D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping"
set "CARLA_DIST=%CARLA_ROOT%\PythonAPI\carla\dist"

echo ============================================
echo CARLA Python Package Installation
echo ============================================
echo.
echo Available CARLA wheels in: %CARLA_DIST%
echo.
dir "%CARLA_DIST%\*.whl"
echo.
echo ============================================
echo.

REM Detect Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo Detected Python version: %PYVER%

REM Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)

echo Python major.minor: %PYMAJOR%.%PYMINOR%
echo.

REM Map to wheel filename
set "WHEEL_FILE="
if "%PYMAJOR%.%PYMINOR%"=="3.8" set "WHEEL_FILE=carla-0.10.0-cp38-cp38-win_amd64.whl"
if "%PYMAJOR%.%PYMINOR%"=="3.9" set "WHEEL_FILE=carla-0.10.0-cp39-cp39-win_amd64.whl"
if "%PYMAJOR%.%PYMINOR%"=="3.10" set "WHEEL_FILE=carla-0.10.0-cp310-cp310-win_amd64.whl"
if "%PYMAJOR%.%PYMINOR%"=="3.11" set "WHEEL_FILE=carla-0.10.0-cp311-cp311-win_amd64.whl"
if "%PYMAJOR%.%PYMINOR%"=="3.12" set "WHEEL_FILE=carla-0.10.0-cp312-cp312-win_amd64.whl"

if "%WHEEL_FILE%"=="" (
    echo ERROR: No compatible CARLA wheel found for Python %PYMAJOR%.%PYMINOR%
    echo Available wheels are for Python 3.8, 3.9, 3.10, 3.11, 3.12
    pause
    exit /b 1
)

echo Installing: %WHEEL_FILE%
echo.

pip install "%CARLA_DIST%\%WHEEL_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo CARLA Python package installed successfully!
    echo ============================================
    echo.
    echo You can verify the installation by running:
    echo   python -c "import carla; print(carla.__file__)"
) else (
    echo.
    echo ERROR: Installation failed!
)

pause

