"""
Scenario Runner for TCP Evaluation
Loads scenario configuration and runs evaluation in CARLA.
"""

import os
import sys
import time
import random
import logging
import argparse
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

import numpy as np

try:
    import carla
except ImportError:
    print("ERROR: CARLA Python API not found. Please install it first.")
    sys.exit(1)

from scenario_schema import (
    ScenarioConfig, load_scenario_config,
    ManeuverType, LocationType, TrafficDensity
)


class ScenarioRunner:
    """
    Runs a scenario based on configuration.
    Handles world setup, traffic spawning, weather, and evaluation.
    """
    
    def __init__(self, config: ScenarioConfig, host: str = "localhost", port: int = 2000):
        self.config = config
        self.host = host
        self.port = port
        
        # CARLA objects
        self.client: Optional[carla.Client] = None
        self.world: Optional[carla.World] = None
        self.traffic_manager: Optional[carla.TrafficManager] = None
        self.map: Optional[carla.Map] = None
        
        # Spawned actors
        self.ego_vehicle: Optional[carla.Vehicle] = None
        self.vehicles: List[carla.Vehicle] = []
        self.pedestrians: List[carla.Walker] = []
        self.pedestrian_controllers: List[carla.WalkerAIController] = []
        self.sensors: List[carla.Sensor] = []
        
        # Route and waypoints
        self.spawn_point: Optional[carla.Transform] = None
        self.destination: Optional[carla.Location] = None
        self.route_waypoints: List[carla.Waypoint] = []
        
        # Metrics
        self.metrics: Dict[str, Any] = {}
        self.start_time: float = 0
        self.collisions: List[Dict] = []
        self.lane_invasions: List[Dict] = []
        self.red_lights_run: int = 0
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging based on config"""
        log_level = getattr(logging, self.config.output.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """Connect to CARLA server"""
        try:
            self.logger.info(f"Connecting to CARLA at {self.host}:{self.port}")
            self.client = carla.Client(self.host, self.port)
            self.client.set_timeout(30.0)
            
            server_version = self.client.get_server_version()
            self.logger.info(f"Connected to CARLA {server_version}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to CARLA: {e}")
            return False
    
    def load_world(self) -> bool:
        """Load the specified town/map"""
        try:
            town = self.config.maneuver.town
            self.logger.info(f"Loading world: {town}")
            
            # Check if we need to change the map
            current_map = self.client.get_world().get_map().name
            if town not in current_map:
                self.world = self.client.load_world(town)
            else:
                self.world = self.client.get_world()
            
            self.map = self.world.get_map()
            self.logger.info(f"World loaded: {self.map.name}")
            
            # Setup traffic manager
            self.traffic_manager = self.client.get_trafficmanager(8000)
            self.traffic_manager.set_synchronous_mode(False)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to load world: {e}")
            return False
    
    def apply_weather(self):
        """Apply weather settings from config"""
        weather_params = self.config.weather.get_weather_params()
        self.logger.info(f"Applying weather preset: {self.config.weather.preset.value}")
        
        weather = carla.WeatherParameters(
            cloudiness=weather_params["cloudiness"],
            precipitation=weather_params["precipitation"],
            precipitation_deposits=weather_params["precipitation_deposits"],
            wind_intensity=weather_params["wind_intensity"],
            fog_density=weather_params["fog_density"],
            fog_distance=weather_params["fog_distance"],
            fog_falloff=weather_params["fog_falloff"],
            wetness=weather_params["wetness"],
            sun_azimuth_angle=weather_params["sun_azimuth_angle"],
            sun_altitude_angle=weather_params["sun_altitude_angle"],
        )
        
        self.world.set_weather(weather)
        self.logger.info("Weather applied successfully")
    
    def apply_friction(self):
        """Apply road friction settings"""
        friction = self.config.road.friction
        self.logger.info(f"Applying road friction: {friction}")
        
        # Create friction trigger for the entire map
        # This affects all vehicles on the road
        blueprint_library = self.world.get_blueprint_library()
        
        # Note: CARLA's friction is applied via physics settings
        # For global friction, we need to modify vehicle physics
        # This will be applied when spawning vehicles
        self.friction_value = friction
    
    def find_maneuver_location(self) -> Tuple[carla.Transform, carla.Location]:
        """
        Find appropriate spawn point and destination for the maneuver type.
        Returns (spawn_transform, destination_location)
        """
        maneuver_type = self.config.maneuver.type
        location_type = self.config.maneuver.location
        
        self.logger.info(f"Finding location for {maneuver_type.value} at {location_type.value}")
        
        spawn_points = self.map.get_spawn_points()
        
        # If specific spawn point is requested
        if self.config.maneuver.spawn_point_index >= 0:
            idx = self.config.maneuver.spawn_point_index
            if idx < len(spawn_points):
                spawn = spawn_points[idx]
                # Calculate destination based on maneuver
                destination = self._calculate_destination(spawn, maneuver_type)
                return spawn, destination
        
        # Find intersection locations
        intersections = self._find_intersections(location_type)
        
        if not intersections:
            self.logger.warning("No suitable intersections found, using random spawn point")
            spawn = random.choice(spawn_points)
            destination = self._calculate_destination(spawn, maneuver_type)
            return spawn, destination
        
        # Find spawn point near an intersection with the right approach for the maneuver
        for intersection_wp in intersections:
            spawn, destination = self._find_maneuver_spawn_at_intersection(
                intersection_wp, maneuver_type
            )
            if spawn is not None:
                return spawn, destination
        
        # Fallback
        self.logger.warning("Could not find ideal maneuver location, using best available")
        spawn = random.choice(spawn_points)
        destination = self._calculate_destination(spawn, maneuver_type)
        return spawn, destination
    
    def _find_intersections(self, location_type: LocationType) -> List[carla.Waypoint]:
        """Find intersections based on location type"""
        intersections = []
        
        # Get all waypoints
        waypoints = self.map.generate_waypoints(5.0)  # 5 meter spacing
        
        for wp in waypoints:
            if wp.is_junction:
                junction = wp.get_junction()
                if junction is None:
                    continue
                
                # Check if it has traffic lights (for signal intersections)
                has_signal = len(self.world.get_traffic_lights_in_junction(junction.id)) > 0
                
                if location_type == LocationType.INTERSECTION_SIGNAL and has_signal:
                    intersections.append(wp)
                elif location_type == LocationType.INTERSECTION_NO_SIGNAL and not has_signal:
                    intersections.append(wp)
                elif location_type == LocationType.ROAD_SEGMENT and not wp.is_junction:
                    intersections.append(wp)
        
        # Remove duplicates (same junction)
        unique_junctions = {}
        for wp in intersections:
            if wp.is_junction:
                junction_id = wp.get_junction().id
                if junction_id not in unique_junctions:
                    unique_junctions[junction_id] = wp
        
        return list(unique_junctions.values())
    
    def _find_maneuver_spawn_at_intersection(
        self, 
        intersection_wp: carla.Waypoint,
        maneuver_type: ManeuverType
    ) -> Tuple[Optional[carla.Transform], Optional[carla.Location]]:
        """Find spawn point before intersection for specific maneuver"""
        
        junction = intersection_wp.get_junction()
        if junction is None:
            return None, None
        
        # Get junction waypoints
        junction_wps = junction.get_waypoints(carla.LaneType.Driving)
        
        for entry_wp, exit_wp in junction_wps:
            # Calculate turn angle
            entry_yaw = entry_wp.transform.rotation.yaw
            exit_yaw = exit_wp.transform.rotation.yaw
            angle_diff = (exit_yaw - entry_yaw + 180) % 360 - 180
            
            # Match maneuver type
            is_match = False
            if maneuver_type == ManeuverType.STRAIGHT and abs(angle_diff) < 30:
                is_match = True
            elif maneuver_type == ManeuverType.LEFT_TURN and -120 < angle_diff < -60:
                is_match = True
            elif maneuver_type == ManeuverType.RIGHT_TURN and 60 < angle_diff < 120:
                is_match = True
            
            if is_match:
                # Find spawn point 30-50 meters before intersection
                spawn_wp = entry_wp.previous(40.0)
                if spawn_wp:
                    spawn_wp = spawn_wp[0]
                    spawn_transform = spawn_wp.transform
                    spawn_transform.location.z += 0.5  # Lift slightly
                    
                    # Destination is after the exit
                    dest_wp = exit_wp.next(30.0)
                    if dest_wp:
                        destination = dest_wp[0].transform.location
                        return spawn_transform, destination
        
        return None, None
    
    def _calculate_destination(
        self, 
        spawn: carla.Transform, 
        maneuver_type: ManeuverType
    ) -> carla.Location:
        """Calculate destination based on spawn point and maneuver type"""
        spawn_wp = self.map.get_waypoint(spawn.location)
        
        # Go forward to find next intersection or destination
        distance = 100.0  # meters
        next_wps = spawn_wp.next(distance)
        
        if next_wps:
            return next_wps[0].transform.location
        else:
            # Fallback: just go forward
            forward = spawn.get_forward_vector()
            dest = carla.Location(
                x=spawn.location.x + forward.x * distance,
                y=spawn.location.y + forward.y * distance,
                z=spawn.location.z
            )
            return dest
    
    def spawn_ego_vehicle(self) -> bool:
        """Spawn the ego vehicle at the maneuver location"""
        try:
            # Find spawn point and destination
            self.spawn_point, self.destination = self.find_maneuver_location()
            
            self.logger.info(f"Spawn point: {self.spawn_point.location}")
            self.logger.info(f"Destination: {self.destination}")
            
            # Get vehicle blueprint
            blueprint_library = self.world.get_blueprint_library()
            vehicle_bp = blueprint_library.find('vehicle.lincoln.mkz2017')
            
            # Set as hero (ego vehicle)
            if vehicle_bp.has_attribute('role_name'):
                vehicle_bp.set_attribute('role_name', 'hero')
            
            # Spawn vehicle
            self.ego_vehicle = self.world.try_spawn_actor(vehicle_bp, self.spawn_point)
            
            if self.ego_vehicle is None:
                self.logger.error("Failed to spawn ego vehicle")
                return False
            
            # Apply friction to vehicle physics
            if hasattr(self, 'friction_value'):
                physics = self.ego_vehicle.get_physics_control()
                for wheel in physics.wheels:
                    wheel.tire_friction = self.friction_value * 3.5  # Scale to CARLA's default
                self.ego_vehicle.apply_physics_control(physics)
            
            self.logger.info(f"Ego vehicle spawned: {self.ego_vehicle.type_id}")
            
            # Move spectator to follow ego
            spectator = self.world.get_spectator()
            spectator.set_transform(carla.Transform(
                self.spawn_point.location + carla.Location(z=50),
                carla.Rotation(pitch=-90)
            ))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to spawn ego vehicle: {e}")
            return False
    
    def spawn_traffic(self):
        """Spawn NPC vehicles and pedestrians based on config"""
        self._spawn_vehicles()
        self._spawn_pedestrians()
    
    def _spawn_vehicles(self):
        """Spawn NPC vehicles with rule-breaking behavior"""
        vehicle_config = self.config.traffic.vehicles
        min_count, max_count = vehicle_config.get_vehicle_count_range()
        
        if max_count == 0:
            self.logger.info("No vehicles to spawn (density: none)")
            return
        
        target_count = random.randint(min_count, max_count)
        self.logger.info(f"Spawning {target_count} NPC vehicles")
        
        blueprint_library = self.world.get_blueprint_library()
        vehicle_bps = blueprint_library.filter('vehicle.*')
        
        # Filter out bikes and motorcycles for more realistic traffic
        vehicle_bps = [bp for bp in vehicle_bps if 
                      'bike' not in bp.id.lower() and 
                      'motorcycle' not in bp.id.lower()]
        
        spawn_points = self.map.get_spawn_points()
        random.shuffle(spawn_points)
        
        spawned = 0
        for spawn_point in spawn_points:
            if spawned >= target_count:
                break
            
            # Don't spawn too close to ego
            if self.ego_vehicle:
                ego_loc = self.ego_vehicle.get_location()
                dist = spawn_point.location.distance(ego_loc)
                if dist < 20:
                    continue
            
            bp = random.choice(vehicle_bps)
            
            # Set as autopilot
            if bp.has_attribute('role_name'):
                bp.set_attribute('role_name', 'autopilot')
            
            vehicle = self.world.try_spawn_actor(bp, spawn_point)
            
            if vehicle:
                vehicle.set_autopilot(True, self.traffic_manager.get_port())
                self._apply_vehicle_behavior(vehicle, vehicle_config)
                self.vehicles.append(vehicle)
                spawned += 1
        
        self.logger.info(f"Spawned {spawned} NPC vehicles")
    
    def _apply_vehicle_behavior(self, vehicle: carla.Vehicle, config):
        """Apply rule-breaking behavior to a vehicle"""
        rule_break_prob = config.rule_break_probability
        behaviors = config.behaviors
        
        # Determine if this vehicle will break rules
        if random.random() > rule_break_prob:
            return  # This vehicle follows rules
        
        tm_port = self.traffic_manager.get_port()
        
        # Apply specific behaviors
        if random.random() < behaviors.run_red_light:
            self.traffic_manager.ignore_lights_percentage(vehicle, 100)
        
        if random.random() < behaviors.ignore_stop_sign:
            self.traffic_manager.ignore_signs_percentage(vehicle, 100)
        
        if random.random() < behaviors.sudden_lane_change:
            self.traffic_manager.random_left_lanechange_percentage(vehicle, 50)
            self.traffic_manager.random_right_lanechange_percentage(vehicle, 50)
        
        if random.random() < behaviors.ignore_right_of_way:
            self.traffic_manager.ignore_vehicles_percentage(vehicle, 50)
        
        if random.random() < behaviors.tailgate:
            self.traffic_manager.distance_to_leading_vehicle(vehicle, 1.0)
        
        # Speed variation
        speed_diff = random.uniform(-20, 30)  # -20% to +30% of speed limit
        self.traffic_manager.vehicle_percentage_speed_difference(vehicle, speed_diff)
    
    def _spawn_pedestrians(self):
        """Spawn pedestrians with rule-breaking behavior"""
        ped_config = self.config.traffic.pedestrians
        min_count, max_count = ped_config.get_pedestrian_count_range()
        
        if max_count == 0:
            self.logger.info("No pedestrians to spawn (density: none)")
            return
        
        target_count = random.randint(min_count, max_count)
        self.logger.info(f"Spawning {target_count} pedestrians")
        
        blueprint_library = self.world.get_blueprint_library()
        walker_bps = blueprint_library.filter('walker.pedestrian.*')
        
        # Get spawn locations on sidewalks
        spawn_locations = []
        for _ in range(target_count * 3):  # Try more locations than needed
            loc = self.world.get_random_location_from_navigation()
            if loc:
                spawn_locations.append(loc)
        
        spawned = 0
        for loc in spawn_locations:
            if spawned >= target_count:
                break
            
            bp = random.choice(walker_bps)
            
            # Set pedestrian speed
            if bp.has_attribute('speed'):
                speed = random.uniform(1.0, 2.0)  # Walking speed
                bp.set_attribute('speed', str(speed))
            
            spawn_transform = carla.Transform(loc)
            walker = self.world.try_spawn_actor(bp, spawn_transform)
            
            if walker:
                self.pedestrians.append(walker)
                
                # Spawn AI controller
                controller_bp = blueprint_library.find('controller.ai.walker')
                controller = self.world.spawn_actor(controller_bp, carla.Transform(), walker)
                
                if controller:
                    self.pedestrian_controllers.append(controller)
                    controller.start()
                    
                    # Set destination
                    dest = self.world.get_random_location_from_navigation()
                    if dest:
                        controller.go_to_location(dest)
                    
                    # Apply rule-breaking behavior
                    self._apply_pedestrian_behavior(controller, walker, ped_config)
                
                spawned += 1
        
        self.logger.info(f"Spawned {spawned} pedestrians")
    
    def _apply_pedestrian_behavior(self, controller, walker, config):
        """Apply rule-breaking behavior to a pedestrian"""
        rule_break_prob = config.rule_break_probability
        behaviors = config.behaviors
        
        if random.random() > rule_break_prob:
            return  # This pedestrian follows rules
        
        # Jaywalking: cross roads at random
        if random.random() < behaviors.jaywalk:
            # Set to cross roads
            controller.set_max_speed(random.uniform(1.5, 3.0))
        
        # Ignore signals
        if random.random() < behaviors.ignore_signal:
            # Pedestrians don't have signal awareness in base CARLA
            # This is handled by their random walking
            pass
        
        # Sudden crossing - handled by setting aggressive destinations
        if random.random() < behaviors.sudden_crossing:
            # Get a location on the road
            ego_loc = self.ego_vehicle.get_location() if self.ego_vehicle else None
            if ego_loc:
                # Set destination near ego path
                offset = carla.Location(
                    x=random.uniform(-10, 10),
                    y=random.uniform(-10, 10),
                    z=0
                )
                road_loc = carla.Location(
                    x=ego_loc.x + offset.x,
                    y=ego_loc.y + offset.y,
                    z=ego_loc.z
                )
                controller.go_to_location(road_loc)
    
    def setup_sensors(self):
        """Setup collision and lane invasion sensors for metrics"""
        if not self.ego_vehicle:
            return
        
        blueprint_library = self.world.get_blueprint_library()
        
        # Collision sensor
        collision_bp = blueprint_library.find('sensor.other.collision')
        collision_sensor = self.world.spawn_actor(
            collision_bp,
            carla.Transform(),
            attach_to=self.ego_vehicle
        )
        collision_sensor.listen(self._on_collision)
        self.sensors.append(collision_sensor)
        
        # Lane invasion sensor
        lane_bp = blueprint_library.find('sensor.other.lane_invasion')
        lane_sensor = self.world.spawn_actor(
            lane_bp,
            carla.Transform(),
            attach_to=self.ego_vehicle
        )
        lane_sensor.listen(self._on_lane_invasion)
        self.sensors.append(lane_sensor)
        
        self.logger.info("Sensors attached to ego vehicle")
    
    def _on_collision(self, event):
        """Callback for collision events"""
        other_actor = event.other_actor
        collision_info = {
            'timestamp': event.timestamp,
            'other_actor': other_actor.type_id if other_actor else 'unknown',
            'impulse': event.normal_impulse,
        }
        self.collisions.append(collision_info)
        self.logger.warning(f"Collision with {collision_info['other_actor']}")
    
    def _on_lane_invasion(self, event):
        """Callback for lane invasion events"""
        lane_types = [str(lt) for lt in event.crossed_lane_markings]
        invasion_info = {
            'timestamp': event.timestamp,
            'lane_types': lane_types,
        }
        self.lane_invasions.append(invasion_info)
    
    def cleanup(self):
        """Clean up all spawned actors"""
        self.logger.info("Cleaning up actors...")
        
        # Destroy sensors
        for sensor in self.sensors:
            if sensor.is_alive:
                sensor.destroy()
        self.sensors.clear()
        
        # Destroy pedestrian controllers
        for controller in self.pedestrian_controllers:
            if controller.is_alive:
                controller.stop()
                controller.destroy()
        self.pedestrian_controllers.clear()
        
        # Destroy pedestrians
        for walker in self.pedestrians:
            if walker.is_alive:
                walker.destroy()
        self.pedestrians.clear()
        
        # Destroy vehicles
        for vehicle in self.vehicles:
            if vehicle.is_alive:
                vehicle.destroy()
        self.vehicles.clear()
        
        # Destroy ego vehicle
        if self.ego_vehicle and self.ego_vehicle.is_alive:
            self.ego_vehicle.destroy()
        self.ego_vehicle = None
        
        self.logger.info("Cleanup complete")
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete scenario.
        Returns metrics dictionary.
        """
        try:
            # Connect and setup
            if not self.connect():
                return {'error': 'Failed to connect to CARLA'}
            
            if not self.load_world():
                return {'error': 'Failed to load world'}
            
            # Apply settings
            self.apply_weather()
            self.apply_friction()
            
            # Spawn actors
            if not self.spawn_ego_vehicle():
                return {'error': 'Failed to spawn ego vehicle'}
            
            self.spawn_traffic()
            self.setup_sensors()
            
            # Print scenario summary
            print("\n" + "="*60)
            print(self.config.summary())
            print("="*60 + "\n")
            
            # Wait for world to settle
            self.world.tick()
            time.sleep(1.0)
            
            self.logger.info("Scenario setup complete. Ready for evaluation.")
            self.logger.info("Ego vehicle is ready for TCP model control.")
            
            # Return initial state
            return {
                'status': 'ready',
                'spawn_point': {
                    'x': self.spawn_point.location.x,
                    'y': self.spawn_point.location.y,
                    'z': self.spawn_point.location.z,
                },
                'destination': {
                    'x': self.destination.x,
                    'y': self.destination.y,
                    'z': self.destination.z,
                },
                'num_vehicles': len(self.vehicles),
                'num_pedestrians': len(self.pedestrians),
            }
            
        except Exception as e:
            self.logger.error(f"Error running scenario: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def get_ego_vehicle(self) -> Optional[carla.Vehicle]:
        """Get the ego vehicle for external control"""
        return self.ego_vehicle
    
    def get_destination(self) -> Optional[carla.Location]:
        """Get the destination location"""
        return self.destination


def main():
    parser = argparse.ArgumentParser(description='Run TCP evaluation scenario')
    parser.add_argument('--config', '-c', type=str, required=True,
                       help='Path to scenario config YAML file')
    parser.add_argument('--host', type=str, default='localhost',
                       help='CARLA server host')
    parser.add_argument('--port', '-p', type=int, default=2000,
                       help='CARLA server port')
    
    args = parser.parse_args()
    
    # Load config
    print(f"Loading scenario config: {args.config}")
    config = load_scenario_config(args.config)
    
    # Create and run scenario
    runner = ScenarioRunner(config, args.host, args.port)
    
    try:
        result = runner.run()
        print("\nScenario Result:")
        print(result)
        
        if result.get('status') == 'ready':
            print("\n" + "="*60)
            print("Scenario is ready!")
            print("The ego vehicle is spawned and waiting for control.")
            print("Press Ctrl+C to cleanup and exit.")
            print("="*60)
            
            # Keep running until interrupted
            while True:
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        runner.cleanup()


if __name__ == "__main__":
    main()

