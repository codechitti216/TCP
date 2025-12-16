@echo off
REM ============================================
REM TCP Evaluation Script for Windows
REM ============================================

REM Load environment variables
call "%~dp0set_env.bat"

REM Challenge settings
set CHALLENGE_TRACK_CODENAME=SENSORS
set PORT=2000
set TM_PORT=8000
set DEBUG_CHALLENGE=0
set REPETITIONS=3
set RESUME=True

REM TCP evaluation configuration
set ROUTES=leaderboard/data/evaluation_routes/routes_lav_valid.xml
set TEAM_AGENT=team_code/tcp_agent.py
REM Set this to your trained model checkpoint path:
set TEAM_CONFIG=PATH_TO_MODEL_CKPT
set CHECKPOINT_ENDPOINT=results_TCP.json
set SCENARIOS=leaderboard/data/scenarios/all_towns_traffic_scenarios.json
set SAVE_PATH=data/results_TCP/

echo ============================================
echo TCP Evaluation
echo ============================================
echo Routes: %ROUTES%
echo Agent: %TEAM_AGENT%
echo Model: %TEAM_CONFIG%
echo Results: %CHECKPOINT_ENDPOINT%
echo Port: %PORT%
echo ============================================
echo.
echo IMPORTANT: Make sure CARLA server is running first!
echo Run start_carla.bat in a separate terminal.
echo.

if "%TEAM_CONFIG%"=="PATH_TO_MODEL_CKPT" (
    echo ERROR: Please set TEAM_CONFIG to your model checkpoint path!
    echo Edit run_evaluation.bat and update the TEAM_CONFIG variable.
    pause
    exit /b 1
)

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
echo Evaluation completed!
pause

