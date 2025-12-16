#!/usr/bin/env python3
"""Check environment sanity: verifies CARLA and basic deps."""
import sys

def main():
    print("Python:", sys.executable, sys.version)
    try:
        import carla
        print("CARLA import OK. carla.__version__:", getattr(carla, '__version__', 'unknown'))
        try:
            world = None
            # If CARLA server is running on default host/port this will succeed quickly
            client = carla.Client('localhost', 2000)
            client.set_timeout(2.0)
            world = client.get_world()
            print("Connected to CARLA server, map:", world.get_map().name)
        except Exception as e:
            print("CARLA server not reachable (this is fine if server not running):", e)
    except Exception as e:
        print("ERROR importing CARLA:", e)
        print("Make sure CARLA Python API is installed (pip install carla==0.9.10 or install from CARLA_ROOT/PythonAPI/carla/dist)")

if __name__ == '__main__':
    main()
