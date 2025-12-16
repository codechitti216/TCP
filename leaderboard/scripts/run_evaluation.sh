#!/bin/bash
set -euo pipefail

# ============================================================
# CARLA SETUP
# ============================================================
export CARLA_ROOT=${CARLA_ROOT:-""}

if [ -z "$CARLA_ROOT" ]; then
	CANDIDATES=(
		"$HOME/carla"
		"/opt/carla"
		"/home/cthalia/E2E/CARLA/carla_0.9.10"
		"/usr/local/share/carla"
	)
	for C in "${CANDIDATES[@]}"; do
		if [ -d "$C" ]; then
			export CARLA_ROOT="$C"
			echo "[SR] Auto-detected CARLA_ROOT=$CARLA_ROOT"
			break
		fi
	done
fi

if [ -z "$CARLA_ROOT" ]; then
	echo "ERROR: CARLA_ROOT not set and auto-detection failed" >&2
	exit 1
fi

export CARLA_SERVER="${CARLA_ROOT}/CarlaUE4.sh"

# CARLA PythonAPI
export PYTHONPATH="${CARLA_ROOT}/PythonAPI:${PYTHONPATH}"
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla:${PYTHONPATH}"

if [ -f "${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg" ]; then
	export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg:${PYTHONPATH}"
fi

# ============================================================
# REPO PATHS (ABSOLUTE, AUTHORITATIVE)
# ============================================================
# This script lives in: leaderboard/scripts/run_evaluation.sh
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[SR] Using repository root: ${REPO_ROOT}"

# These three are NON-NEGOTIABLE
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH}"
export PYTHONPATH="${REPO_ROOT}/leaderboard:${PYTHONPATH}"
export PYTHONPATH="${REPO_ROOT}/leaderboard/team_code:${PYTHONPATH}"
export PYTHONPATH="${REPO_ROOT}/scenario_runner:${PYTHONPATH}"

echo "[SR] PYTHONPATH resolved to:"
python3 - <<PY
import sys
print("\n".join(sys.path))
PY

export LEADERBOARD_ROOT="leaderboard"
export CHALLENGE_TRACK_CODENAME="SENSORS"

# ============================================================
# NETWORK
# ============================================================
export PORT=${PORT:-2000}
export TM_PORT=${TM_PORT:-8000}

# ============================================================
# PIPELINE CONTRACT (MUST BE PROVIDED)
# ============================================================
: "${ROUTES:?ROUTES must be set by pipeline}"
: "${TEAM_CONFIG:?TEAM_CONFIG must be set by pipeline}"

export REPETITIONS=1
export RESUME=False
export DEBUG_CHALLENGE=${DEBUG_CHALLENGE:-1}
DEBUG_CHALLENGE=$( [ "$DEBUG_CHALLENGE" = "True" ] && echo 1 || echo "$DEBUG_CHALLENGE" )
DEBUG_CHALLENGE=$( [ "$DEBUG_CHALLENGE" = "False" ] && echo 0 || echo "$DEBUG_CHALLENGE" )

# Optional (used for logging / debugging)
export INTENDED_SCENARIO_TYPE=${INTENDED_SCENARIO_TYPE:-""}

# ============================================================
# AGENT + DATA
# ============================================================
export TEAM_AGENT=${TEAM_AGENT:-leaderboard/team_code/tcp_agent.py}
export CHECKPOINT_ENDPOINT=${CHECKPOINT_ENDPOINT:-results_TCP.json}
export SCENARIOS=${SCENARIOS:-leaderboard/data/scenarios/all_towns_traffic_scenarios.json}
export SAVE_PATH=${SAVE_PATH:-data/results_TCP/}
export RECORD_PATH=${RECORD_PATH:-""}

# ============================================================
# SANITY CHECKS
# ============================================================
echo "[SR] ROUTES                = $ROUTES"
echo "[SR] TEAM_AGENT            = $TEAM_AGENT"
echo "[SR] TEAM_CONFIG           = $TEAM_CONFIG"
echo "[SR] SCENARIOS             = $SCENARIOS"
echo "[SR] INTENDED_SCENARIO     = ${INTENDED_SCENARIO_TYPE:-<none>}"

[ -f "$ROUTES" ] || { echo "ERROR: ROUTES not found: $ROUTES" >&2; exit 2; }
[ -f "$TEAM_CONFIG" ] || { echo "ERROR: TEAM_CONFIG not found: $TEAM_CONFIG" >&2; exit 2; }
[ -f "$SCENARIOS" ] || { echo "ERROR: SCENARIOS not found: $SCENARIOS" >&2; exit 2; }

# ============================================================
# PYTHON IMPORT VERIFICATION (FAIL FAST)
# ============================================================
python3 - <<PY
import carla
import srunner
import leaderboard
print("[SR] Python imports OK")
print("[SR] srunner path:", srunner.__file__)
print("[SR] leaderboard path:", leaderboard.__file__)
PY

# ============================================================
# CARLA AVAILABILITY
# ============================================================
python3 - <<PY
import carla
client = carla.Client("localhost", int(${PORT}))
client.set_timeout(3.0)
try:
	client.get_world()
except Exception as e:
	print("ERROR: CARLA not responding:", e)
	raise SystemExit(3)
print("[SR] Connected to CARLA")
PY

# ============================================================
# RUN EVALUATION (FULL OWNERSHIP TRANSFER)
# ============================================================
exec python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
	--scenarios=${SCENARIOS} \
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
