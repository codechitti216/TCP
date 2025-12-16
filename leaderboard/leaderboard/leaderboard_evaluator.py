#!/usr/bin/env python
"""
CARLA Challenge Evaluator Routes
"""

from __future__ import print_function

import traceback
import argparse
from argparse import RawTextHelpFormatter
import importlib
import os
import sys
import gc
import pkg_resources
import carla
import signal
import time
import inspect

from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.timer import GameTime
from srunner.scenariomanager.watchdog import Watchdog

from leaderboard.scenarios.scenario_manager import ScenarioManager
from leaderboard.scenarios.route_scenario import RouteScenario
from leaderboard.envs.sensor_interface import SensorConfigurationInvalid
from leaderboard.autoagents.agent_wrapper import AgentWrapper
from leaderboard.utils.statistics_manager import StatisticsManager
from leaderboard.utils.route_indexer import RouteIndexer


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
sensors_to_icons = {
    'sensor.camera.rgb': 'carla_camera',
    'sensor.camera.semantic_segmentation': 'carla_camera',
    'sensor.camera.depth': 'carla_camera',
    'sensor.lidar.ray_cast': 'carla_lidar',
    'sensor.lidar.ray_cast_semantic': 'carla_lidar',
    'sensor.other.radar': 'carla_radar',
    'sensor.other.gnss': 'carla_gnss',
    'sensor.other.imu': 'carla_imu',
    'sensor.opendrive_map': 'carla_opendrive_map',
    'sensor.speedometer': 'carla_speedometer'
}


# -----------------------------------------------------------------------------
# EVALUATOR
# -----------------------------------------------------------------------------
class LeaderboardEvaluator(object):

    ego_vehicles = []

    client_timeout = 10.0
    frame_rate = 20.0

    def __init__(self, args, statistics_manager):

        self.statistics_manager = statistics_manager
        self.sensors = None
        self.sensor_icons = []
        self._vehicle_lights = (
            carla.VehicleLightState.Position | carla.VehicleLightState.LowBeam
        )

        # ------------------------------------------------------------------
        # SCENARIO INTENT (🔥 CORE FIX 🔥)
        # ------------------------------------------------------------------
        self.intended_scenario = os.environ.get("INTENDED_SCENARIO_TYPE", "").strip()
        if self.intended_scenario:
            print(f"[EVAL] Enforcing scenario type: {self.intended_scenario}")
        else:
            print("[EVAL] No scenario intent specified (free mix mode)")

        # ------------------------------------------------------------------
        # CARLA CLIENT
        # ------------------------------------------------------------------
        self.client = carla.Client(args.host, int(args.port))
        if args.timeout:
            self.client_timeout = float(args.timeout)
        self.client.set_timeout(self.client_timeout)

        self.traffic_manager = self.client.get_trafficmanager(
            int(args.trafficManagerPort)
        )

        # ------------------------------------------------------------------
        # LOAD AGENT
        # ------------------------------------------------------------------
        module_name = os.path.basename(args.agent).split('.')[0]
        sys.path.insert(0, os.path.dirname(args.agent))
        self.module_agent = importlib.import_module(module_name)

        # ------------------------------------------------------------------
        # MANAGER
        # ------------------------------------------------------------------
        self.manager = ScenarioManager(args.timeout, args.debug > 1)
        self._agent_watchdog = Watchdog(int(float(args.timeout)))
        signal.signal(signal.SIGINT, self._signal_handler)

    # ------------------------------------------------------------------
    def _signal_handler(self, signum, frame):
        if self._agent_watchdog and not self._agent_watchdog.get_status():
            raise RuntimeError("Timeout: Agent setup stalled")
        if self.manager:
            self.manager.signal_handler(signum, frame)

    # ------------------------------------------------------------------
    def _cleanup(self):

        if self.manager and self.manager.get_running_status():
            if hasattr(self, 'world') and self.world:
                settings = self.world.get_settings()
                settings.synchronous_mode = False
                settings.fixed_delta_seconds = None
                self.world.apply_settings(settings)
                self.traffic_manager.set_synchronous_mode(False)

        if self.manager:
            self.manager.cleanup()

        CarlaDataProvider.cleanup()

        for v in self.ego_vehicles:
            if v:
                v.destroy()
        self.ego_vehicles = []

        if self._agent_watchdog:
            self._agent_watchdog.stop()

        if hasattr(self, 'agent_instance') and self.agent_instance:
            self.agent_instance.destroy()
            self.agent_instance = None

    # ------------------------------------------------------------------
    def _load_and_wait_for_world(self, args, town):

        self.traffic_manager.set_synchronous_mode(False)

        existing = CarlaDataProvider.get_world()
        if existing and existing.get_map().name == town:
            self.world = existing
            print(f"[EVAL] Reusing world {town}")
        else:
            self.world = self.client.load_world(town)

        settings = self.world.get_settings()
        settings.fixed_delta_seconds = 1.0 / self.frame_rate
        settings.synchronous_mode = True
        self.world.apply_settings(settings)

        CarlaDataProvider.set_client(self.client)
        CarlaDataProvider.set_world(self.world)
        CarlaDataProvider._blueprint_library = self.world.get_blueprint_library()
        CarlaDataProvider.set_traffic_manager_port(int(args.trafficManagerPort))

        self.traffic_manager.set_synchronous_mode(True)
        self.world.tick()

        if self.world.get_map().name != town:
            raise RuntimeError(f"Wrong map loaded: expected {town}")

    # ------------------------------------------------------------------
    def _load_and_run_scenario(self, args, config):

        print(f"\n[EVAL] ===== Running {config.name} ({config.scenario_type}) =====")

        self.statistics_manager.set_route(config.name, config.index)

        # ------------------ Agent ------------------
        try:
            self._agent_watchdog.start()
            agent_class = getattr(self.module_agent, 'get_entry_point')()
            self.agent_instance = getattr(self.module_agent, agent_class)(args.agent_config)
            config.agent = self.agent_instance

            if not self.sensors:
                self.sensors = self.agent_instance.sensors()
                AgentWrapper.validate_sensor_configuration(
                    self.sensors, self.agent_instance.track, args.track
                )
                self.sensor_icons = [sensors_to_icons[s['type']] for s in self.sensors]
                self.statistics_manager.save_sensors(self.sensor_icons, args.checkpoint)

            self._agent_watchdog.stop()

        except Exception as e:
            traceback.print_exc()
            self._cleanup()
            return

        # ------------------ World ------------------
        self._load_and_wait_for_world(args, config.town)

        # ------------------ Ego ------------------
        for ev in config.ego_vehicles:
            actor = CarlaDataProvider.request_new_actor(
                ev.model, ev.transform, ev.rolename
            )
            self.ego_vehicles.append(actor)

        self.world.tick()

        # ------------------ Scenario ------------------
        scenario = RouteScenario(self.world, config, debug_mode=args.debug)
        self.statistics_manager.set_scenario(scenario.scenario)

        self.manager.load_scenario(scenario, self.agent_instance, config.repetition_index)
        self.manager.run_scenario()

        self.manager.stop_scenario()
        scenario.remove_all_actors()
        self._cleanup()

    # ------------------------------------------------------------------
    def run(self, args):

        route_indexer = RouteIndexer(args.routes, args.scenarios, args.repetitions)
        print(f"[EVAL] Loaded {route_indexer.total} route configs")

        if not args.resume:
            self.statistics_manager.clear_record(args.checkpoint)
            route_indexer.save_state(args.checkpoint)

        executed_any = False

        while route_indexer.peek():
            config = route_indexer.next()

            # 🔒 HARD SCENARIO ENFORCEMENT
            if self.intended_scenario:
                if config.scenario_type != self.intended_scenario:
                    print(f"[SKIP] {config.name} ({config.scenario_type})")
                    continue

            executed_any = True
            self._load_and_run_scenario(args, config)
            route_indexer.save_state(args.checkpoint)

        if self.intended_scenario and not executed_any:
            raise RuntimeError(
                f"No routes matched scenario {self.intended_scenario}"
            )

        print("[EVAL] Evaluation finished cleanly")


# -----------------------------------------------------------------------------
def main():

    parser = argparse.ArgumentParser(
        formatter_class=RawTextHelpFormatter
    )

    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='2000')
    parser.add_argument('--trafficManagerPort', default='8000')
    parser.add_argument('--timeout', default='200.0')
    parser.add_argument('--routes', required=True)
    parser.add_argument('--scenarios', required=True)
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('-a', '--agent', required=True)
    parser.add_argument('--agent-config', default='')
    parser.add_argument('--track', default='SENSORS')
    parser.add_argument('--checkpoint', default='simulation_results.json')
    parser.add_argument('--debug', type=int, default=0)
    parser.add_argument('--resume', action='store_true')

    args = parser.parse_args()

    stats = StatisticsManager()
    evaluator = LeaderboardEvaluator(args, stats)
    evaluator.run(args)


if __name__ == '__main__':
    main()
