#!/bin/bash
# install_carla.sh - Download and extract CARLA 0.9.10.1 (Linux)
# Usage: ./scripts/install_carla.sh [install_dir]

set -euo pipefail
INSTALL_DIR=${1:-"$HOME/carla"}
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

CARLA_VERSION="CARLA_0.9.10.1"
CARLA_TGZ="$CARLA_VERSION.tar.gz"
ADDITIONAL_TGZ="AdditionalMaps_0.9.10.1.tar.gz"

echo "This will download CARLA 0.9.10.1 and AdditionalMaps into $INSTALL_DIR"
read -p "Proceed? [y/N] " yn
if [[ "$yn" != "y" && "$yn" != "Y" ]]; then
  echo "Aborted"
  exit 1
fi

wget -c https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/${CARLA_TGZ}
wget -c https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/${ADDITIONAL_TGZ}

tar -xf ${CARLA_TGZ}
rm ${CARLA_TGZ}

tar -xf ${ADDITIONAL_TGZ}
rm ${ADDITIONAL_TGZ}

echo "CARLA downloaded and extracted to $INSTALL_DIR"

echo "To run CARLA:"
echo "  cd ${INSTALL_DIR} && ./CarlaUE4.sh --world-port=2000 -opengl"

echo "Set CARLA_ROOT to this path, e.g. export CARLA_ROOT=${INSTALL_DIR}"