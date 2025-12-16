#!/usr/bin/env python3
"""
Sanity pipeline (TWO-PHASE OWNERSHIP):

Phase 1 (this process):
  - Launch UI (traffic, weather, time)
  - Wait for world_ready marker
  - Launch BEV route selector
  - Wait for VALID trajectory marker
  - Generate route XML
  - Launch ScenarioRunner / Leaderboard in a NEW PROCESS
  - Exit

Phase 2 (ScenarioRunner process):
  - Owns CARLA
  - Owns ticking
  - Owns ego, sensors, cleanup
"""

import argparse
import json
import os
import sys
import time
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

# -----------------------------------------------------------------------------
# PATH SETUP
# -----------------------------------------------------------------------------
repo_root = Path(__file__).resolve().parents[1]
sanity_dir = Path(__file__).resolve().parent

if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def load_trajectory(path: Path):
    with open(path, "r") as f:
        data = json.load(f)

    if "trajectory" not in data:
        raise RuntimeError("Trajectory JSON missing 'trajectory' key")

    if "intended_scenario" not in data:
        raise RuntimeError("Trajectory missing intended_scenario (BEV contract broken)")

    traj = data["trajectory"]
    if len(traj) < 2:
        raise RuntimeError("Trajectory too short")

    traj = sorted(traj, key=lambda x: x["index"])

    return data["intended_scenario"], traj


def write_route_xml(traj, town_name: str) -> Path:
    routes_root = ET.Element("routes")
    route_el = ET.SubElement(routes_root, "route")
    route_el.set("id", "1")
    route_el.set("town", town_name)

    for p in traj:
        wp = ET.SubElement(route_el, "waypoint")
        wp.set("x", str(p["x"]))
        wp.set("y", str(p["y"]))
        wp.set("z", str(p.get("z", 0.0)))

    out = Path.cwd() / f"temp_route_{int(time.time())}.xml"
    ET.ElementTree(routes_root).write(out)
    return out


def wait_for_file(path: Path, label: str):
    print(f"[PIPELINE] Waiting for {label}...")
    while not path.exists():
        time.sleep(0.25)


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-config", required=True)
    args = parser.parse_args()

    world_marker = sanity_dir / ".world_ready"
    traj_marker = sanity_dir / ".last_traj"

    # Clean stale markers
    for m in (world_marker, traj_marker):
        if m.exists():
            m.unlink()

    # -------------------------------------------------------------------------
    # PHASE 1A: UI CONTROLLER
    # -------------------------------------------------------------------------
    print("[PIPELINE] Launching UI controller")
    subprocess.Popen(
        [sys.executable, str(sanity_dir / "ui_controller.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    wait_for_file(world_marker, "world_ready marker")
    print("[PIPELINE] World configuration locked")

    # -------------------------------------------------------------------------
    # PHASE 1B: BEV ROUTE SELECTION
    # -------------------------------------------------------------------------
    print("[PIPELINE] Launching BEV route selector")
    subprocess.Popen(
        [sys.executable, str(sanity_dir / "bev_route_selector.py")],
        stdout=None,
        stderr=None,
    )

    wait_for_file(traj_marker, "trajectory marker")

    traj_name = traj_marker.read_text().strip()
    traj_path = None

    for p in [Path.cwd() / traj_name, sanity_dir / traj_name]:
        if p.exists():
            traj_path = p
            break

    if traj_path is None:
        raise RuntimeError(f"Trajectory file not found: {traj_name}")

    print(f"[PIPELINE] Loading trajectory: {traj_path}")

    intended_scenario, traj = load_trajectory(traj_path)

    print("[PIPELINE] Intended scenario:")
    print(f"  Type : {intended_scenario['scenario']}")
    print(f"  Pose : ({intended_scenario['x']:.1f}, {intended_scenario['y']:.1f})")

    # NOTE: Town must match UI world
    town = "Town03"

    # -------------------------------------------------------------------------
    # PHASE 1C: ROUTE XML
    # -------------------------------------------------------------------------
    route_xml = write_route_xml(traj, town)
    print(f"[PIPELINE] Route XML written: {route_xml}")

    # -------------------------------------------------------------------------
    # PHASE 2: SCENARIORUNNER (FULL OWNERSHIP)
    # -------------------------------------------------------------------------
    env = os.environ.copy()
    env["ROUTES"] = str(route_xml)
    env["TEAM_CONFIG"] = args.agent_config
    env["REPETITIONS"] = "1"
    env["RESUME"] = "False"
    env["DEBUG_CHALLENGE"] = "True"

    # Propagate scenario intent explicitly
    env["INTENDED_SCENARIO_TYPE"] = intended_scenario["scenario"]

    run_script = repo_root / "leaderboard/scripts/run_evaluation.sh"

    print("[PIPELINE] Launching ScenarioRunner (handoff complete)")
    ret = subprocess.call([str(run_script)], env=env)

    print(f"[PIPELINE] ScenarioRunner exited with code {ret}")
    print("[PIPELINE] Orchestration process exiting cleanly")


if __name__ == "__main__":
    main()
