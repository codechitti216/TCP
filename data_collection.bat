@echo off
REM ============================================
REM TCP Data Collection Script for Windows
REM ============================================

REM Load environment variables
call "%~dp0set_env.bat"

REM Challenge settings
set CHALLENGE_TRACK_CODENAME=SENSORS
set PORT=2000
set TM_PORT=8000
set DEBUG_CHALLENGE=0
set REPETITIONS=1
set RESUME=True
set DATA_COLLECTION=True

REM Data collection configuration
REM Change ROUTES to collect data from different towns
set ROUTES=leaderboard/data/TCP_training_routes/routes_town01.xml
set TEAM_AGENT=team_code/roach_ap_agent.py
set TEAM_CONFIG=roach/config/config_agent.yaml
set CHECKPOINT_ENDPOINT=data_collect_town01_results.json
set SCENARIOS=leaderboard/data/scenarios/all_towns_traffic_scenarios.json
set SAVE_PATH=data/data_collect_town01_results/

echo ============================================
echo TCP Data Collection
echo ============================================
echo Routes: %ROUTES%
echo Agent: %TEAM_AGENT%
echo Save Path: %SAVE_PATH%
echo Port: %PORT%
echo ============================================
echo.
echo IMPORTANT: Make sure CARLA server is running first!
echo Run start_carla.bat in a separate terminal.
echo.
pause

cd /d "%TCP_ROOT%"

python "%LEADERBOARD_ROOT%\leaderboard\leaderboard_evaluator.py" ^
    --scenarios=%SCENARIOS% ^
    --routes=%ROUTES% ^
    --repetitions=%REPETITIONS% ^
    --track=%CHALLENGE_TRACK_CODENAME% ^
    --checkpoint=%CHECKPOINT_ENDPOINT% ^
    --agent=%TEAM_AGENT% ^
    --agent-config=%TEAM_CONFIG% ^
    --debug=%DEBUG_CHALLENGE% ^
    --resume=%RESUME% ^
    --port=%PORT% ^
    --trafficManagerPort=%TM_PORT%

echo.
echo Data collection completed!
pause

