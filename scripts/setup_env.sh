#!/bin/bash
# setup_env.sh - Create 'TCP' conda environment and install CARLA client
# Usage: ./scripts/setup_env.sh [--force]

set -euo pipefail

FORCE=0
if [ "${1:-}" = "--force" ]; then
  FORCE=1
fi

ENV_NAME=TCP
ENV_FILE=environment.yml

# Check conda availability
if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found. Please install Anaconda / Miniconda and retry." >&2
  exit 1
fi

# Create environment if not exists (or --force to recreate)
EXISTS=$(conda env list | awk '{print $1}' | grep -x ${ENV_NAME} || true)
if [ -n "$EXISTS" ] && [ "$FORCE" -eq 0 ]; then
  echo "Conda env '$ENV_NAME' already exists. Use --force to recreate or 'conda activate $ENV_NAME'."
else
  if [ -n "$EXISTS" ] && [ "$FORCE" -eq 1 ]; then
    echo "Removing existing env '$ENV_NAME'..."
    conda remove -y -n $ENV_NAME --all
  fi

  echo "Creating conda environment '$ENV_NAME' from $ENV_FILE..."
  conda env create -f $ENV_FILE --name $ENV_NAME
fi

echo "Activating environment and installing CARLA client..."
# shellcheck disable=SC1091
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $ENV_NAME

# Try to install CARLA wheel/egg from CARLA_ROOT if available
if [ -n "${CARLA_ROOT:-}" ]; then
  LOCAL_WHEEL=$(ls -1 "$CARLA_ROOT"/PythonAPI/carla/dist/* 2>/dev/null | head -n1 || true)
  if [ -n "$LOCAL_WHEEL" ]; then
    echo "Found CARLA wheel/egg at: $LOCAL_WHEEL"
    pip install --upgrade "$LOCAL_WHEEL"
    echo "Installed CARLA from local wheel/egg."
    exit 0
  else
    echo "CARLA_ROOT is set but no wheel/egg found under $CARLA_ROOT/PythonAPI/carla/dist" >&2
  fi
fi

# Fallback: try to pip install carla==0.9.10 (may work for some Python versions)
echo "Attempting to pip install carla==0.9.10 from PyPI (may or may not be available for your Python)"
if pip install --no-cache-dir "carla==0.9.10"; then
  echo "Installed carla==0.9.10 from PyPI"
else
  echo "Failed to install carla from PyPI.\nIf you have CARLA installed locally, set CARLA_ROOT to the CARLA install root so the local wheel is used. Example: export CARLA_ROOT=~/carla && ./scripts/setup_env.sh" >&2
  exit 1
fi
