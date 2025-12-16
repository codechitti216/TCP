@echo off
REM ============================================
REM Run TCP Scenario Evaluation
REM ============================================

REM Load environment variables
call "%~dp0set_env.bat"

set CONFIG_FILE=%1

if "%CONFIG_FILE%"=="" (
    echo Usage: run_scenario.bat ^<config_file^>
    echo.
    echo Available presets:
    echo   scenario_config\presets\straight_easy.yaml
    echo   scenario_config\presets\left_turn_medium.yaml
    echo   scenario_config\presets\right_turn_hard.yaml
    echo   scenario_config\presets\night_fog_challenge.yaml
    echo   scenario_config\example_scenario.yaml
    echo.
    echo Example:
    echo   run_scenario.bat scenario_config\presets\left_turn_medium.yaml
    pause
    exit /b 1
)

echo ============================================
echo Running Scenario: %CONFIG_FILE%
echo ============================================
echo.
echo IMPORTANT: Make sure CARLA server is running first!
echo Run start_carla.bat in a separate terminal.
echo.
pause

cd /d "%TCP_ROOT%"

python scenario_config\scenario_runner.py --config "%CONFIG_FILE%"

echo.
echo Scenario completed!
pause

