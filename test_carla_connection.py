#!/usr/bin/env python
"""
CARLA Connection Test Script
Tests connection to a running CARLA server and displays basic info.
"""

import sys
import time
import argparse

def test_carla_connection(host='localhost', port=2000, timeout=10):
    """
    Test connection to CARLA server.
    
    Args:
        host: CARLA server hostname
        port: CARLA server port
        timeout: Connection timeout in seconds
    
    Returns:
        True if connection successful, False otherwise
    """
    print("=" * 60)
    print("CARLA Connection Test")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Timeout: {timeout}s")
    print("=" * 60)
    print()
    
    # Try to import carla
    print("[1/4] Importing CARLA Python API...")
    try:
        import carla
        print(f"      ✓ CARLA module imported successfully")
        print(f"      ✓ CARLA module location: {carla.__file__}")
    except ImportError as e:
        print(f"      ✗ Failed to import CARLA: {e}")
        print()
        print("SOLUTION: Run 'install_carla.bat' to install the CARLA Python package")
        return False
    
    # Try to connect to server
    print()
    print(f"[2/4] Connecting to CARLA server at {host}:{port}...")
    try:
        client = carla.Client(host, port)
        client.set_timeout(timeout)
        print(f"      ✓ Client created")
    except Exception as e:
        print(f"      ✗ Failed to create client: {e}")
        return False
    
    # Get server version
    print()
    print("[3/4] Getting server information...")
    try:
        server_version = client.get_server_version()
        client_version = client.get_client_version()
        print(f"      ✓ Server version: {server_version}")
        print(f"      ✓ Client version: {client_version}")
        
        if server_version != client_version:
            print()
            print(f"      ⚠ WARNING: Version mismatch!")
            print(f"        Server: {server_version}")
            print(f"        Client: {client_version}")
            print(f"        This may cause compatibility issues.")
    except Exception as e:
        print(f"      ✗ Failed to get server version: {e}")
        print()
        print("SOLUTION: Make sure CARLA server is running (run 'start_carla.bat')")
        return False
    
    # Get world info
    print()
    print("[4/4] Getting world information...")
    try:
        world = client.get_world()
        settings = world.get_settings()
        weather = world.get_weather()
        map_name = world.get_map().name
        
        print(f"      ✓ Connected to world successfully")
        print(f"      ✓ Current map: {map_name}")
        print(f"      ✓ Synchronous mode: {settings.synchronous_mode}")
        print(f"      ✓ Fixed delta seconds: {settings.fixed_delta_seconds}")
        
        # Get available maps
        available_maps = client.get_available_maps()
        print(f"      ✓ Available maps ({len(available_maps)}):")
        for m in sorted(available_maps)[:10]:  # Show first 10
            print(f"          - {m}")
        if len(available_maps) > 10:
            print(f"          ... and {len(available_maps) - 10} more")
            
    except Exception as e:
        print(f"      ✗ Failed to get world info: {e}")
        return False
    
    # Get actors
    print()
    print("[BONUS] Current actors in world...")
    try:
        actors = world.get_actors()
        vehicles = actors.filter('vehicle.*')
        walkers = actors.filter('walker.*')
        traffic_lights = actors.filter('traffic.traffic_light')
        
        print(f"      ✓ Total actors: {len(actors)}")
        print(f"      ✓ Vehicles: {len(vehicles)}")
        print(f"      ✓ Pedestrians: {len(walkers)}")
        print(f"      ✓ Traffic lights: {len(traffic_lights)}")
    except Exception as e:
        print(f"      ⚠ Could not get actors: {e}")
    
    print()
    print("=" * 60)
    print("✓ CONNECTION SUCCESSFUL!")
    print("=" * 60)
    print()
    print("CARLA is running and ready for use.")
    print("You can now run data_collection.bat or run_evaluation.bat")
    print()
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Test CARLA server connection')
    parser.add_argument('--host', default='localhost', help='CARLA server host (default: localhost)')
    parser.add_argument('--port', '-p', type=int, default=2000, help='CARLA server port (default: 2000)')
    parser.add_argument('--timeout', '-t', type=int, default=10, help='Connection timeout in seconds (default: 10)')
    
    args = parser.parse_args()
    
    success = test_carla_connection(args.host, args.port, args.timeout)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

