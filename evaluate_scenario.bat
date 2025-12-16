@echo off
REM ============================================
REM Evaluate TCP Model on Scenario
REM ============================================

REM Load environment variables
call "%~dp0set_env.bat"

set CONFIG_FILE=%1

if "%CONFIG_FILE%"=="" (
    echo Usage: evaluate_scenario.bat ^<config_file^>
    echo.
    echo Available presets:
    echo   scenario_config\presets\straight_easy.yaml
    echo   scenario_config\presets\left_turn_medium.yaml
    echo   scenario_config\presets\right_turn_hard.yaml
    echo   scenario_config\presets\night_fog_challenge.yaml
    echo   scenario_config\example_scenario.yaml
    echo.
    echo Example:
    echo   evaluate_scenario.bat scenario_config\presets\left_turn_medium.yaml
    pause
    exit /b 1
)

echo ============================================
echo Evaluating TCP Model on Scenario
echo Config: %CONFIG_FILE%
echo ============================================
echo.
echo IMPORTANT: 
echo   1. Make sure CARLA server is running (start_carla.bat)
echo   2. Set the model checkpoint path in the config file
echo.
pause

cd /d "%TCP_ROOT%"

python scenario_config\tcp_evaluator.py --config "%CONFIG_FILE%"

echo.
echo Evaluation completed!
echo Results saved to evaluation_results folder.
pause

