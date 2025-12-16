#!/usr/bin/env python3
"""
Minimal CARLA connection test with vehicle and sensors
"""

import sys
import time
import numpy as np

try:
    import carla
    print("✅ CARLA Python API loaded")
except ImportError:
    print("❌ CARLA not found")
    sys.exit(1)


def main():
    vehicle = None
    lidar_sensor = None
    imu_sensor = None
    
    try:
        # Connect to CARLA
        print("Connecting to CARLA...")
        client = carla.Client("localhost", 2000)
        client.set_timeout(10.0)
        
        # Get current world
        world = client.get_world()
        print(f"✅ Connected to CARLA world: {world.get_map().name}")
        
        # Get blueprint library
        blueprint_library = world.get_blueprint_library()
        
        # Find vehicle blueprint
        vehicle_bp = blueprint_library.filter('vehicle.*')[0]
        print(f"Using vehicle: {vehicle_bp.id}")
        
        # Get spawn points
        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            print("❌ No spawn points available")
            return 1
        
        # Spawn vehicle
        vehicle = world.try_spawn_actor(vehicle_bp, spawn_points[0])
        if vehicle is None:
            print("❌ Failed to spawn vehicle")
            return 1
        
        print(f"✅ Vehicle spawned at {vehicle.get_location()}")
        
        # Setup LiDAR
        lidar_bp = blueprint_library.find('sensor.lidar.ray_cast')
        lidar_bp.set_attribute('channels', '64')
        lidar_bp.set_attribute('range', '100')
        lidar_bp.set_attribute('rotation_frequency', '10')
        
        lidar_transform = carla.Transform(carla.Location(x=0.0, z=2.0))
        lidar_sensor = world.spawn_actor(lidar_bp, lidar_transform, attach_to=vehicle)
        
        print("✅ LiDAR sensor created")
        
        # Setup IMU
        imu_bp = blueprint_library.find('sensor.other.imu')
        imu_sensor = world.spawn_actor(imu_bp, carla.Transform(), attach_to=vehicle)
        
        print("✅ IMU sensor created")
        
        # Data counters
        lidar_count = 0
        imu_count = 0
        
        def lidar_callback(data):
            nonlocal lidar_count
            lidar_count += 1
            if lidar_count % 10 == 0:
                points = np.frombuffer(data.raw_data, dtype=np.float32).reshape(-1, 4)
                print(f"LiDAR frame {lidar_count}: {len(points)} points")
        
        def imu_callback(data):
            nonlocal imu_count
            imu_count += 1
            if imu_count % 50 == 0:
                print(f"IMU frame {imu_count}: acc={data.accelerometer}, gyro={data.gyroscope}")
        
        # Start listening
        lidar_sensor.listen(lidar_callback)
        imu_sensor.listen(imu_callback)
        
        # Enable autopilot
        vehicle.set_autopilot(True)
        print("✅ Autopilot enabled")
        
        print("\n🚀 Starting data collection for 30 seconds...")
        print("Press Ctrl+C to stop early")
        
        # Run for 30 seconds
        start_time = time.time()
        try:
            while time.time() - start_time < 30:
                world.wait_for_tick()
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
        
        print(f"\n📊 Final counts:")
        print(f"   - LiDAR frames: {lidar_count}")
        print(f"   - IMU frames: {imu_count}")
        print("✅ Test completed successfully!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        if lidar_sensor is not None:
            lidar_sensor.destroy()
        if imu_sensor is not None:
            imu_sensor.destroy()
        if vehicle is not None:
            vehicle.destroy()
        print("✅ Cleanup complete")


if __name__ == "__main__":
    sys.exit(main())

