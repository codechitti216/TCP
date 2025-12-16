"""
Scenario Configuration Schema and Dataclasses
Defines the structure for scenario configuration with validation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import yaml


class ManeuverType(Enum):
    STRAIGHT = "straight"
    LEFT_TURN = "left_turn"
    RIGHT_TURN = "right_turn"


class LocationType(Enum):
    INTERSECTION_SIGNAL = "intersection_signal"
    INTERSECTION_NO_SIGNAL = "intersection_no_signal"
    ROAD_SEGMENT = "road_segment"


class TrafficDensity(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WeatherPreset(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    WET = "wet"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"
    NIGHT = "night"
    CUSTOM = "custom"


# Density to count mappings
VEHICLE_DENSITY_MAP = {
    TrafficDensity.NONE: (0, 0),
    TrafficDensity.LOW: (10, 20),
    TrafficDensity.MEDIUM: (30, 50),
    TrafficDensity.HIGH: (60, 100),
}

PEDESTRIAN_DENSITY_MAP = {
    TrafficDensity.NONE: (0, 0),
    TrafficDensity.LOW: (5, 10),
    TrafficDensity.MEDIUM: (15, 30),
    TrafficDensity.HIGH: (40, 60),
}

# Weather presets
WEATHER_PRESETS = {
    WeatherPreset.CLEAR: {
        "cloudiness": 10.0,
        "precipitation": 0.0,
        "precipitation_deposits": 0.0,
        "wind_intensity": 5.0,
        "fog_density": 0.0,
        "fog_distance": 0.0,
        "fog_falloff": 0.0,
        "wetness": 0.0,
        "sun_azimuth_angle": 45.0,
        "sun_altitude_angle": 70.0,
    },
    WeatherPreset.CLOUDY: {
        "cloudiness": 80.0,
        "precipitation": 0.0,
        "precipitation_deposits": 0.0,
        "wind_intensity": 20.0,
        "fog_density": 0.0,
        "fog_distance": 0.0,
        "fog_falloff": 0.0,
        "wetness": 0.0,
        "sun_azimuth_angle": 45.0,
        "sun_altitude_angle": 45.0,
    },
    WeatherPreset.WET: {
        "cloudiness": 50.0,
        "precipitation": 0.0,
        "precipitation_deposits": 40.0,
        "wind_intensity": 10.0,
        "fog_density": 5.0,
        "fog_distance": 50.0,
        "fog_falloff": 1.0,
        "wetness": 60.0,
        "sun_azimuth_angle": 45.0,
        "sun_altitude_angle": 45.0,
    },
    WeatherPreset.RAIN: {
        "cloudiness": 80.0,
        "precipitation": 60.0,
        "precipitation_deposits": 50.0,
        "wind_intensity": 30.0,
        "fog_density": 10.0,
        "fog_distance": 75.0,
        "fog_falloff": 1.0,
        "wetness": 80.0,
        "sun_azimuth_angle": 45.0,
        "sun_altitude_angle": 30.0,
    },
    WeatherPreset.HEAVY_RAIN: {
        "cloudiness": 100.0,
        "precipitation": 100.0,
        "precipitation_deposits": 100.0,
        "wind_intensity": 80.0,
        "fog_density": 30.0,
        "fog_distance": 50.0,
        "fog_falloff": 2.0,
        "wetness": 100.0,
        "sun_azimuth_angle": 45.0,
        "sun_altitude_angle": 15.0,
    },
    WeatherPreset.FOG: {
        "cloudiness": 50.0,
        "precipitation": 0.0,
        "precipitation_deposits": 20.0,
        "wind_intensity": 5.0,
        "fog_density": 80.0,
        "fog_distance": 10.0,
        "fog_falloff": 2.0,
        "wetness": 30.0,
        "sun_azimuth_angle": 45.0,
        "sun_altitude_angle": 30.0,
    },
    WeatherPreset.NIGHT: {
        "cloudiness": 20.0,
        "precipitation": 0.0,
        "precipitation_deposits": 0.0,
        "wind_intensity": 5.0,
        "fog_density": 5.0,
        "fog_distance": 50.0,
        "fog_falloff": 1.0,
        "wetness": 0.0,
        "sun_azimuth_angle": 270.0,
        "sun_altitude_angle": -80.0,
    },
}


@dataclass
class VehicleBehaviors:
    """Vehicle rule-breaking behavior probabilities"""
    run_red_light: float = 0.0
    ignore_stop_sign: float = 0.0
    sudden_lane_change: float = 0.0
    ignore_right_of_way: float = 0.0
    sudden_brake: float = 0.0
    tailgate: float = 0.0
    
    def __post_init__(self):
        for attr in ['run_red_light', 'ignore_stop_sign', 'sudden_lane_change',
                     'ignore_right_of_way', 'sudden_brake', 'tailgate']:
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")


@dataclass
class PedestrianBehaviors:
    """Pedestrian rule-breaking behavior probabilities"""
    jaywalk: float = 0.0
    ignore_signal: float = 0.0
    sudden_crossing: float = 0.0
    stop_in_road: float = 0.0
    
    def __post_init__(self):
        for attr in ['jaywalk', 'ignore_signal', 'sudden_crossing', 'stop_in_road']:
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")


@dataclass
class VehicleTrafficConfig:
    """Vehicle traffic configuration"""
    density: TrafficDensity = TrafficDensity.MEDIUM
    rule_break_probability: float = 0.0
    behaviors: VehicleBehaviors = field(default_factory=VehicleBehaviors)
    
    def __post_init__(self):
        if isinstance(self.density, str):
            self.density = TrafficDensity(self.density)
        if isinstance(self.behaviors, dict):
            self.behaviors = VehicleBehaviors(**self.behaviors)
        if not 0.0 <= self.rule_break_probability <= 1.0:
            raise ValueError(f"rule_break_probability must be between 0.0 and 1.0")
    
    def get_vehicle_count_range(self) -> tuple:
        """Get min/max vehicle count for this density"""
        return VEHICLE_DENSITY_MAP[self.density]


@dataclass
class PedestrianTrafficConfig:
    """Pedestrian traffic configuration"""
    density: TrafficDensity = TrafficDensity.LOW
    rule_break_probability: float = 0.0
    behaviors: PedestrianBehaviors = field(default_factory=PedestrianBehaviors)
    
    def __post_init__(self):
        if isinstance(self.density, str):
            self.density = TrafficDensity(self.density)
        if isinstance(self.behaviors, dict):
            self.behaviors = PedestrianBehaviors(**self.behaviors)
        if not 0.0 <= self.rule_break_probability <= 1.0:
            raise ValueError(f"rule_break_probability must be between 0.0 and 1.0")
    
    def get_pedestrian_count_range(self) -> tuple:
        """Get min/max pedestrian count for this density"""
        return PEDESTRIAN_DENSITY_MAP[self.density]


@dataclass
class TrafficConfig:
    """Combined traffic configuration"""
    vehicles: VehicleTrafficConfig = field(default_factory=VehicleTrafficConfig)
    pedestrians: PedestrianTrafficConfig = field(default_factory=PedestrianTrafficConfig)
    
    def __post_init__(self):
        if isinstance(self.vehicles, dict):
            self.vehicles = VehicleTrafficConfig(**self.vehicles)
        if isinstance(self.pedestrians, dict):
            self.pedestrians = PedestrianTrafficConfig(**self.pedestrians)


@dataclass
class CustomWeather:
    """Custom weather parameters"""
    cloudiness: float = 0.0
    precipitation: float = 0.0
    precipitation_deposits: float = 0.0
    wind_intensity: float = 0.0
    fog_density: float = 0.0
    fog_distance: float = 0.0
    fog_falloff: float = 0.0
    wetness: float = 0.0
    sun_azimuth_angle: float = 45.0
    sun_altitude_angle: float = 70.0


@dataclass
class WeatherConfig:
    """Weather configuration"""
    preset: WeatherPreset = WeatherPreset.CLEAR
    custom: CustomWeather = field(default_factory=CustomWeather)
    
    def __post_init__(self):
        if isinstance(self.preset, str):
            self.preset = WeatherPreset(self.preset)
        if isinstance(self.custom, dict):
            self.custom = CustomWeather(**self.custom)
    
    def get_weather_params(self) -> dict:
        """Get the actual weather parameters to apply"""
        if self.preset == WeatherPreset.CUSTOM:
            return {
                "cloudiness": self.custom.cloudiness,
                "precipitation": self.custom.precipitation,
                "precipitation_deposits": self.custom.precipitation_deposits,
                "wind_intensity": self.custom.wind_intensity,
                "fog_density": self.custom.fog_density,
                "fog_distance": self.custom.fog_distance,
                "fog_falloff": self.custom.fog_falloff,
                "wetness": self.custom.wetness,
                "sun_azimuth_angle": self.custom.sun_azimuth_angle,
                "sun_altitude_angle": self.custom.sun_altitude_angle,
            }
        else:
            return WEATHER_PRESETS[self.preset]


@dataclass
class RoadConfig:
    """Road conditions configuration"""
    friction: float = 1.0
    
    def __post_init__(self):
        if not 0.0 <= self.friction <= 1.0:
            raise ValueError(f"friction must be between 0.0 and 1.0, got {self.friction}")


@dataclass
class ManeuverConfig:
    """Maneuver configuration"""
    type: ManeuverType = ManeuverType.STRAIGHT
    location: LocationType = LocationType.INTERSECTION_SIGNAL
    town: str = "Town03"
    spawn_point_index: int = -1
    
    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = ManeuverType(self.type)
        if isinstance(self.location, str):
            self.location = LocationType(self.location)


@dataclass
class SuccessCriteria:
    """Success criteria for evaluation"""
    complete_maneuver: bool = True
    no_collision: bool = True
    obey_traffic_lights: bool = True
    stay_in_lane: bool = True


@dataclass
class EvaluationConfig:
    """Evaluation settings"""
    timeout: float = 120.0
    stuck_timeout: float = 30.0
    stuck_speed_threshold: float = 0.5
    success: SuccessCriteria = field(default_factory=SuccessCriteria)
    metrics: List[str] = field(default_factory=lambda: [
        "completion_time", "distance_traveled", "average_speed", "max_speed",
        "num_collisions", "collision_types", "red_lights_run", "lane_invasions",
        "route_deviation", "comfort_score"
    ])
    
    def __post_init__(self):
        if isinstance(self.success, dict):
            self.success = SuccessCriteria(**self.success)


@dataclass
class ModelConfig:
    """Model configuration"""
    checkpoint: str = ""
    device: str = "cuda"


@dataclass
class OutputConfig:
    """Output and logging configuration"""
    results_dir: str = "evaluation_results"
    save_video: bool = True
    video_fps: int = 20
    save_sensor_data: bool = False
    save_logs: bool = True
    log_level: str = "info"


@dataclass
class ScenarioConfig:
    """Complete scenario configuration"""
    name: str = "unnamed_scenario"
    description: str = ""
    maneuver: ManeuverConfig = field(default_factory=ManeuverConfig)
    traffic: TrafficConfig = field(default_factory=TrafficConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    road: RoadConfig = field(default_factory=RoadConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    def __post_init__(self):
        if isinstance(self.maneuver, dict):
            self.maneuver = ManeuverConfig(**self.maneuver)
        if isinstance(self.traffic, dict):
            self.traffic = TrafficConfig(**self.traffic)
        if isinstance(self.weather, dict):
            self.weather = WeatherConfig(**self.weather)
        if isinstance(self.road, dict):
            self.road = RoadConfig(**self.road)
        if isinstance(self.evaluation, dict):
            self.evaluation = EvaluationConfig(**self.evaluation)
        if isinstance(self.model, dict):
            self.model = ModelConfig(**self.model)
        if isinstance(self.output, dict):
            self.output = OutputConfig(**self.output)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'ScenarioConfig':
        """Load configuration from YAML file"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Handle nested 'scenario' key if present
        if 'scenario' in data:
            name = data['scenario'].get('name', 'unnamed')
            description = data['scenario'].get('description', '')
        else:
            name = data.get('name', 'unnamed')
            description = data.get('description', '')
        
        return cls(
            name=name,
            description=description,
            maneuver=data.get('maneuver', {}),
            traffic=data.get('traffic', {}),
            weather=data.get('weather', {}),
            road=data.get('road', {}),
            evaluation=data.get('evaluation', {}),
            model=data.get('model', {}),
            output=data.get('output', {}),
        )
    
    def to_yaml(self, yaml_path: str):
        """Save configuration to YAML file"""
        def to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                result = {}
                for field_name in obj.__dataclass_fields__:
                    value = getattr(obj, field_name)
                    result[field_name] = to_dict(value)
                return result
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, list):
                return [to_dict(item) for item in obj]
            else:
                return obj
        
        data = {
            'scenario': {
                'name': self.name,
                'description': self.description,
            },
            'maneuver': to_dict(self.maneuver),
            'traffic': to_dict(self.traffic),
            'weather': to_dict(self.weather),
            'road': to_dict(self.road),
            'evaluation': to_dict(self.evaluation),
            'model': to_dict(self.model),
            'output': to_dict(self.output),
        }
        
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def summary(self) -> str:
        """Return a human-readable summary of the scenario"""
        lines = [
            f"Scenario: {self.name}",
            f"  Description: {self.description}",
            f"  Maneuver: {self.maneuver.type.value} at {self.maneuver.location.value}",
            f"  Town: {self.maneuver.town}",
            f"  Vehicle Traffic: {self.traffic.vehicles.density.value} (rule break: {self.traffic.vehicles.rule_break_probability:.0%})",
            f"  Pedestrian Traffic: {self.traffic.pedestrians.density.value} (rule break: {self.traffic.pedestrians.rule_break_probability:.0%})",
            f"  Weather: {self.weather.preset.value}",
            f"  Road Friction: {self.road.friction:.2f}",
            f"  Timeout: {self.evaluation.timeout}s",
        ]
        return "\n".join(lines)


# Convenience function to load config
def load_scenario_config(yaml_path: str) -> ScenarioConfig:
    """Load a scenario configuration from a YAML file"""
    return ScenarioConfig.from_yaml(yaml_path)


if __name__ == "__main__":
    # Test loading the example config
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    example_path = os.path.join(script_dir, "example_scenario.yaml")
    
    if os.path.exists(example_path):
        config = load_scenario_config(example_path)
        print(config.summary())
        print("\nWeather params:", config.weather.get_weather_params())
        print("Vehicle count range:", config.traffic.vehicles.get_vehicle_count_range())
    else:
        print(f"Example config not found at {example_path}")

