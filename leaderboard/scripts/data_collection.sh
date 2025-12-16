#!/bin/bash
export CARLA_ROOT=${CARLA_ROOT:-""}
if [ -n "$CARLA_ROOT" ]; then
	export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
	export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
	export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
	export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
else
	# Try auto-detection similar to run_evaluation.sh
	CANDIDATES=("$HOME/carla" "/opt/carla" "/home/cthalia/E2E/CARLA/carla_0.9.10" "/usr/local/share/carla")
	for C in "${CANDIDATES[@]}"; do
		if [ -d "$C" ]; then
			export CARLA_ROOT="$C"
			echo "Auto-detected CARLA_ROOT=$CARLA_ROOT"
			break
		fi
	done
	if [ -z "$CARLA_ROOT" ]; then
		echo "Warning: CARLA_ROOT not set. Set CARLA_ROOT to your CARLA install to enable data collection." >&2
	else
		export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
		export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
		export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
		if [ -f "${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg" ]; then
			export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
		fi
	fi
fi
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:scenario_runner

export LEADERBOARD_ROOT=leaderboard
export CHALLENGE_TRACK_CODENAME=SENSORS
export PORT=2000
export TM_PORT=8000
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs
export RESUME=True
export DATA_COLLECTION=True


# Roach data collection
export ROUTES=leaderboard/data/TCP_training_routes/routes_town01.xml
export TEAM_AGENT=team_code/roach_ap_agent.py
export TEAM_CONFIG=roach/config/config_agent.yaml
export CHECKPOINT_ENDPOINT=data_collect_town01_results.json
export SCENARIOS=leaderboard/data/scenarios/all_towns_traffic_scenarios.json
export SAVE_PATH=data/data_collect_town01_results/



python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--record=${RECORD_PATH} \
--resume=${RESUME} \
--port=${PORT} \
--trafficManagerPort=${TM_PORT}


