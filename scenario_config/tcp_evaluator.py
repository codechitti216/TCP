"""
TCP Model Evaluator with Scenario Configuration
Runs the TCP model on configured scenarios and collects metrics.
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import carla
except ImportError:
    print("ERROR: CARLA Python API not found")
    sys.exit(1)

try:
    import torch
    from torchvision import transforms as T
    from PIL import Image
except ImportError:
    print("ERROR: PyTorch not found")
    sys.exit(1)

from scenario_schema import ScenarioConfig, load_scenario_config, ManeuverType
from scenario_runner import ScenarioRunner


@dataclass
class EvaluationMetrics:
    """Metrics collected during evaluation"""
    scenario_name: str = ""
    maneuver_type: str = ""
    
    # Completion
    completed: bool = False
    completion_time: float = 0.0
    timeout_reached: bool = False
    stuck: bool = False
    
    # Distance
    distance_traveled: float = 0.0
    distance_to_destination: float = 0.0
    
    # Speed
    average_speed: float = 0.0
    max_speed: float = 0.0
    min_speed: float = float('inf')
    
    # Safety
    num_collisions: int = 0
    collision_types: List[str] = None
    red_lights_run: int = 0
    lane_invasions: int = 0
    
    # Comfort
    max_acceleration: float = 0.0
    max_deceleration: float = 0.0
    max_lateral_acceleration: float = 0.0
    comfort_score: float = 0.0
    
    # Route
    route_deviation: float = 0.0
    
    def __post_init__(self):
        if self.collision_types is None:
            self.collision_types = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TCPEvaluator:
    """
    Evaluates TCP model performance on configured scenarios.
    """
    
    def __init__(self, config: ScenarioConfig, host: str = "localhost", port: int = 2000):
        self.config = config
        self.host = host
        self.port = port
        
        # Scenario runner
        self.runner: Optional[ScenarioRunner] = None
        
        # TCP model
        self.model = None
        self.device = config.model.device
        
        # State tracking
        self.metrics = EvaluationMetrics()
        self.start_time: float = 0
        self.start_location: Optional[carla.Location] = None
        self.last_location: Optional[carla.Location] = None
        self.last_velocity: Optional[carla.Vector3D] = None
        self.last_time: float = 0
        
        # Speed history for averaging
        self.speed_history: List[float] = []
        self.acceleration_history: List[float] = []
        
        # Stuck detection
        self.stuck_start_time: Optional[float] = None
        
        # Image transform for TCP
        self._im_transform = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        log_level = getattr(logging, self.config.output.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_model(self) -> bool:
        """Load the TCP model from checkpoint"""
        checkpoint_path = self.config.model.checkpoint
        
        if not checkpoint_path or checkpoint_path == "path/to/model/checkpoint.pth":
            self.logger.warning("No model checkpoint specified, running without model")
            return False
        
        if not os.path.exists(checkpoint_path):
            self.logger.error(f"Model checkpoint not found: {checkpoint_path}")
            return False
        
        try:
            self.logger.info(f"Loading TCP model from {checkpoint_path}")
            
            # Import TCP model
            from TCP.model import TCP
            from TCP.config import GlobalConfig
            
            # Load config and model
            tcp_config = GlobalConfig()
            self.model = TCP(tcp_config)
            
            # Load weights
            checkpoint = torch.load(checkpoint_path, map_location=self.device)
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
                # Remove 'model.' prefix if present
                state_dict = {k.replace('model.', ''): v for k, v in state_dict.items()}
            else:
                state_dict = checkpoint
            
            self.model.load_state_dict(state_dict, strict=False)
            self.model = self.model.to(self.device)
            self.model.eval()
            
            self.logger.info("TCP model loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def setup_scenario(self) -> bool:
        """Setup the scenario using ScenarioRunner"""
        self.runner = ScenarioRunner(self.config, self.host, self.port)
        result = self.runner.run()
        
        if result.get('status') != 'ready':
            self.logger.error(f"Failed to setup scenario: {result}")
            return False
        
        # Initialize metrics
        self.metrics.scenario_name = self.config.name
        self.metrics.maneuver_type = self.config.maneuver.type.value
        
        return True
    
    def get_camera_image(self) -> Optional[np.ndarray]:
        """Get camera image from ego vehicle (placeholder - needs sensor setup)"""
        # This would need a camera sensor attached to the ego vehicle
        # For now, return None and use manual control
        return None
    
    def compute_control(self, image: np.ndarray, speed: float, target_point: tuple, command: int) -> tuple:
        """
        Compute control using TCP model.
        Returns (steer, throttle, brake)
        """
        if self.model is None:
            return 0.0, 0.0, 0.0
        
        try:
            with torch.no_grad():
                # Prepare image
                img_tensor = self._im_transform(Image.fromarray(image)).unsqueeze(0)
                img_tensor = img_tensor.to(self.device, dtype=torch.float32)
                
                # Prepare state
                speed_tensor = torch.tensor([[speed / 12.0]]).to(self.device, dtype=torch.float32)
                target_tensor = torch.tensor([target_point]).to(self.device, dtype=torch.float32)
                
                # Command one-hot
                cmd_one_hot = [0] * 6
                cmd_one_hot[command] = 1
                cmd_tensor = torch.tensor([cmd_one_hot]).to(self.device, dtype=torch.float32)
                
                # Combine state
                state = torch.cat([speed_tensor, target_tensor, cmd_tensor], dim=1)
                
                # Forward pass
                pred = self.model(img_tensor, state, target_tensor)
                
                # Get control from waypoints using PID
                velocity = torch.tensor([[speed]]).to(self.device)
                steer, throttle, brake, _ = self.model.control_pid(
                    pred['pred_wp'], velocity, target_tensor
                )
                
                return float(steer), float(throttle), float(brake)
                
        except Exception as e:
            self.logger.error(f"Error computing control: {e}")
            return 0.0, 0.0, 0.0
    
    def update_metrics(self, ego_vehicle: carla.Vehicle, current_time: float):
        """Update metrics based on current state"""
        location = ego_vehicle.get_location()
        velocity = ego_vehicle.get_velocity()
        
        # Speed
        speed = np.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        self.speed_history.append(speed)
        self.metrics.max_speed = max(self.metrics.max_speed, speed)
        self.metrics.min_speed = min(self.metrics.min_speed, speed)
        
        # Distance traveled
        if self.last_location:
            dist = location.distance(self.last_location)
            self.metrics.distance_traveled += dist
        
        # Acceleration
        if self.last_velocity and self.last_time > 0:
            dt = current_time - self.last_time
            if dt > 0:
                accel_x = (velocity.x - self.last_velocity.x) / dt
                accel_y = (velocity.y - self.last_velocity.y) / dt
                accel = np.sqrt(accel_x**2 + accel_y**2)
                self.acceleration_history.append(accel)
                
                # Longitudinal acceleration
                forward = ego_vehicle.get_transform().get_forward_vector()
                long_accel = accel_x * forward.x + accel_y * forward.y
                if long_accel > 0:
                    self.metrics.max_acceleration = max(self.metrics.max_acceleration, long_accel)
                else:
                    self.metrics.max_deceleration = max(self.metrics.max_deceleration, abs(long_accel))
        
        # Distance to destination
        if self.runner and self.runner.destination:
            self.metrics.distance_to_destination = location.distance(self.runner.destination)
        
        # Stuck detection
        if speed < self.config.evaluation.stuck_speed_threshold:
            if self.stuck_start_time is None:
                self.stuck_start_time = current_time
            elif current_time - self.stuck_start_time > self.config.evaluation.stuck_timeout:
                self.metrics.stuck = True
        else:
            self.stuck_start_time = None
        
        # Update last values
        self.last_location = location
        self.last_velocity = velocity
        self.last_time = current_time
    
    def check_completion(self) -> bool:
        """Check if maneuver is completed"""
        if not self.runner or not self.runner.destination or not self.runner.ego_vehicle:
            return False
        
        ego_loc = self.runner.ego_vehicle.get_location()
        dest = self.runner.destination
        
        # Consider completed if within 5 meters of destination
        distance = ego_loc.distance(dest)
        return distance < 5.0
    
    def finalize_metrics(self, elapsed_time: float):
        """Finalize metrics at end of evaluation"""
        self.metrics.completion_time = elapsed_time
        
        # Average speed
        if self.speed_history:
            self.metrics.average_speed = np.mean(self.speed_history)
        
        # Comfort score (based on acceleration variance)
        if self.acceleration_history:
            accel_variance = np.var(self.acceleration_history)
            # Lower variance = higher comfort (scale 0-100)
            self.metrics.comfort_score = max(0, 100 - accel_variance * 10)
        
        # Get collision info from runner
        if self.runner:
            self.metrics.num_collisions = len(self.runner.collisions)
            self.metrics.collision_types = [c['other_actor'] for c in self.runner.collisions]
            self.metrics.lane_invasions = len(self.runner.lane_invasions)
            self.metrics.red_lights_run = self.runner.red_lights_run
    
    def run_evaluation(self) -> EvaluationMetrics:
        """
        Run the complete evaluation.
        Returns collected metrics.
        """
        try:
            # Setup scenario
            if not self.setup_scenario():
                self.metrics.completed = False
                return self.metrics
            
            # Load model (optional)
            self.load_model()
            
            ego_vehicle = self.runner.get_ego_vehicle()
            if not ego_vehicle:
                self.logger.error("No ego vehicle available")
                return self.metrics
            
            # Initialize
            self.start_time = time.time()
            self.start_location = ego_vehicle.get_location()
            self.last_location = self.start_location
            
            self.logger.info("Starting evaluation loop...")
            self.logger.info(f"Timeout: {self.config.evaluation.timeout}s")
            self.logger.info(f"Destination: {self.runner.destination}")
            
            # Main evaluation loop
            step = 0
            while True:
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                # Check timeout
                if elapsed > self.config.evaluation.timeout:
                    self.logger.info("Timeout reached")
                    self.metrics.timeout_reached = True
                    break
                
                # Check stuck
                if self.metrics.stuck:
                    self.logger.info("Vehicle is stuck")
                    break
                
                # Check completion
                if self.check_completion():
                    self.logger.info("Maneuver completed!")
                    self.metrics.completed = True
                    break
                
                # Update metrics
                self.update_metrics(ego_vehicle, elapsed)
                
                # If model is loaded, compute and apply control
                if self.model:
                    # Get camera image (would need sensor)
                    image = self.get_camera_image()
                    if image is not None:
                        speed = np.sqrt(
                            ego_vehicle.get_velocity().x**2 + 
                            ego_vehicle.get_velocity().y**2
                        )
                        # Compute target point in local coords
                        # (simplified - would need proper route planning)
                        target_point = (0, 10)  # Forward
                        command = 3  # Lane follow
                        
                        steer, throttle, brake = self.compute_control(
                            image, speed, target_point, command
                        )
                        
                        control = carla.VehicleControl(
                            throttle=throttle,
                            steer=steer,
                            brake=brake
                        )
                        ego_vehicle.apply_control(control)
                
                # Tick
                self.runner.world.tick()
                step += 1
                
                # Log progress periodically
                if step % 100 == 0:
                    self.logger.info(
                        f"Step {step}: elapsed={elapsed:.1f}s, "
                        f"dist_to_dest={self.metrics.distance_to_destination:.1f}m, "
                        f"speed={self.speed_history[-1] if self.speed_history else 0:.1f}m/s"
                    )
                
                time.sleep(0.05)  # ~20 Hz
            
            # Finalize
            elapsed = time.time() - self.start_time
            self.finalize_metrics(elapsed)
            
            return self.metrics
            
        except KeyboardInterrupt:
            self.logger.info("Evaluation interrupted by user")
            elapsed = time.time() - self.start_time
            self.finalize_metrics(elapsed)
            return self.metrics
            
        except Exception as e:
            self.logger.error(f"Error during evaluation: {e}")
            import traceback
            traceback.print_exc()
            return self.metrics
            
        finally:
            if self.runner:
                self.runner.cleanup()
    
    def save_results(self, output_path: Optional[str] = None):
        """Save evaluation results to file"""
        if output_path is None:
            # Create output directory
            results_dir = self.config.output.results_dir
            os.makedirs(results_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.config.name}_{timestamp}.json"
            output_path = os.path.join(results_dir, filename)
        
        results = {
            'scenario_config': {
                'name': self.config.name,
                'description': self.config.description,
                'maneuver': self.config.maneuver.type.value,
                'location': self.config.maneuver.location.value,
                'town': self.config.maneuver.town,
                'weather': self.config.weather.preset.value,
                'friction': self.config.road.friction,
                'vehicle_density': self.config.traffic.vehicles.density.value,
                'pedestrian_density': self.config.traffic.pedestrians.density.value,
            },
            'metrics': self.metrics.to_dict(),
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description='Evaluate TCP model on scenario')
    parser.add_argument('--config', '-c', type=str, required=True,
                       help='Path to scenario config YAML file')
    parser.add_argument('--host', type=str, default='localhost',
                       help='CARLA server host')
    parser.add_argument('--port', '-p', type=int, default=2000,
                       help='CARLA server port')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output path for results JSON')
    
    args = parser.parse_args()
    
    # Load config
    print(f"Loading scenario config: {args.config}")
    config = load_scenario_config(args.config)
    
    print("\n" + "="*60)
    print(config.summary())
    print("="*60 + "\n")
    
    # Create evaluator and run
    evaluator = TCPEvaluator(config, args.host, args.port)
    metrics = evaluator.run_evaluation()
    
    # Print results
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"Completed: {metrics.completed}")
    print(f"Completion Time: {metrics.completion_time:.1f}s")
    print(f"Distance Traveled: {metrics.distance_traveled:.1f}m")
    print(f"Average Speed: {metrics.average_speed:.1f} m/s")
    print(f"Max Speed: {metrics.max_speed:.1f} m/s")
    print(f"Collisions: {metrics.num_collisions}")
    print(f"Lane Invasions: {metrics.lane_invasions}")
    print(f"Comfort Score: {metrics.comfort_score:.1f}/100")
    print(f"Stuck: {metrics.stuck}")
    print(f"Timeout: {metrics.timeout_reached}")
    print("="*60 + "\n")
    
    # Save results
    output_path = evaluator.save_results(args.output)
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()

