import carla
import random
import time
import threading
import tkinter as tk
from tkinter import ttk
from carla import WeatherParameters

# -------------------------------------------------
# CONSTANTS (MATCH CLI SCRIPT)
# -------------------------------------------------
TM_PORT = 8000

SPAWN_BATCH_SIZE = 6
SPAWN_DELAY_SEC = 0.25

AUTOPILOT_BATCH_SIZE = 4
AUTOPILOT_DELAY_SEC = 0.6


class CarlaUIController:
    def __init__(self, master):
        self.master = master
        self.master.title("CARLA Scenario Controller (CLI-Equivalent)")

        # -------------------------------------------------
        # CARLA CONNECTION
        # -------------------------------------------------
        self.client = carla.Client("localhost", 2000)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()

        self.tm = self.client.get_trafficmanager(TM_PORT)
        self.tm.set_synchronous_mode(False)

        print("Connected to CARLA:", self.world.get_map().name)

        # -------------------------------------------------
        # STATE
        # -------------------------------------------------
        self.vehicles = []
        self.walkers = []
        self.walker_controllers = []

        # -------------------------------------------------
        # UI
        # -------------------------------------------------
        self.build_controls()
        self.build_environment_controls()

    # =================================================
    # UI
    # =================================================
    def build_controls(self):
        frame = ttk.LabelFrame(self.master, text="Traffic (CLI Logic)")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.vehicle_count = tk.StringVar(value="50")
        self.ped_count = tk.StringVar(value="30")

        self._entry(frame, "Vehicles", self.vehicle_count)
        self._entry(frame, "Pedestrians", self.ped_count)

        ttk.Button(
            frame,
            text="Spawn Traffic (SAFE)",
            command=self.spawn_threaded
        ).pack(fill="x", pady=10)
        # Button to mark the world setup as ready for pipeline
        ttk.Button(
            frame,
            text="Set World (Ready)",
            command=self.mark_world_ready
        ).pack(fill="x", pady=5)

    def mark_world_ready(self):
        """Create a small marker file to indicate the world has been set up."""
        try:
            import pathlib
            marker = pathlib.Path(__file__).resolve().parent / '.world_ready'
            marker.write_text(str(time.time()))
            print(f"[UI] World marked ready -> {marker}")
            # Close the UI since the world is ready and we want the UI to end
            try:
                print('[UI] Closing UI after world ready')
                self.master.destroy()
            except Exception:
                pass
        except Exception as e:
            print(f"[UI] Failed to write world ready marker: {e}")

    # =================================================
    # THREAD ENTRY (CRITICAL)
    # =================================================
    def spawn_threaded(self):
        # Never block Tkinter loop
        t = threading.Thread(target=self.spawn_all)
        t.daemon = True
        t.start()

    # =================================================
    # CLI-EQUIVALENT LOGIC
    # =================================================
    def spawn_all(self):
        num_vehicles = int(self.vehicle_count.get())
        num_peds = int(self.ped_count.get())

        print(f"Spawning {num_vehicles} vehicles")
        self.spawn_vehicles(num_vehicles)

        print("Registering vehicles with Traffic Manager")
        self.register_vehicles_with_tm()

        print(f"Spawning {num_peds} pedestrians")
        self.spawn_pedestrians(num_peds)

        print("Traffic ready.")

    # =================================================
    # VEHICLES (PHASE 1: SPAWN ONLY)
    # =================================================
    def spawn_vehicles(self, count):
        spawn_points = self.world.get_map().get_spawn_points()
        blueprints = self.world.get_blueprint_library().filter("vehicle.*")

        random.shuffle(spawn_points)

        max_allowed = min(count, len(spawn_points))
        print(f"[Vehicles] Spawning {max_allowed}")

        for i in range(0, max_allowed, SPAWN_BATCH_SIZE):
            for sp in spawn_points[i:i + SPAWN_BATCH_SIZE]:
                bp = random.choice(blueprints)
                v = self.world.try_spawn_actor(bp, sp)
                if v:
                    self.vehicles.append(v)
            time.sleep(SPAWN_DELAY_SEC)

    # =================================================
    # VEHICLES (PHASE 2: TM REGISTRATION)
    # =================================================
    def register_vehicles_with_tm(self):
        for i in range(0, len(self.vehicles), AUTOPILOT_BATCH_SIZE):
            batch = self.vehicles[i:i + AUTOPILOT_BATCH_SIZE]

            for v in batch:
                if not v.is_alive:
                    continue
                try:
                    v.set_autopilot(True, TM_PORT)
                except RuntimeError as e:
                    print(f"[TM] Failed vehicle {v.id}: {e}")
                    v.destroy()

            time.sleep(AUTOPILOT_DELAY_SEC)

        print(f"[TM] Registered {len(self.vehicles)} vehicles")

    # =================================================
    # PEDESTRIANS (UNCHANGED FROM CLI)
    # =================================================
    def spawn_pedestrians(self, count):
        w_bps = self.world.get_blueprint_library().filter("walker.pedestrian.*")
        c_bp = self.world.get_blueprint_library().find("controller.ai.walker")

        valid_locations = []
        for _ in range(count * 4):
            loc = self.world.get_random_location_from_navigation()
            if loc:
                valid_locations.append(loc)

        max_allowed = min(count, len(valid_locations))
        print(f"[Pedestrians] Spawning {max_allowed}")

        for i in range(0, max_allowed, SPAWN_BATCH_SIZE):
            batch = valid_locations[i:i + SPAWN_BATCH_SIZE]
            cmds = []

            for loc in batch:
                bp = random.choice(w_bps)
                cmds.append(carla.command.SpawnActor(bp, carla.Transform(loc)))

            results = self.client.apply_batch_sync(cmds, True)

            for r in results:
                if r.error:
                    continue

                walker = self.world.get_actor(r.actor_id)
                controller = self.world.spawn_actor(
                    c_bp, carla.Transform(), walker
                )
                controller.start()
                controller.go_to_location(
                    self.world.get_random_location_from_navigation()
                )
                controller.set_max_speed(random.uniform(0.9, 1.4))

                self.walkers.append(walker)
                self.walker_controllers.append(controller)

            time.sleep(SPAWN_DELAY_SEC)

    # =================================================
    # ENVIRONMENT (SAFE, LIVE)
    # =================================================
    def build_environment_controls(self):
        frame = ttk.LabelFrame(self.master, text="Environment")
        frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.cloud = tk.DoubleVar(value=0)
        self.rain = tk.DoubleVar(value=0)
        self.fog = tk.DoubleVar(value=0)
        self.sun = tk.DoubleVar(value=45)

        self._slider(frame, "Cloudiness", 0, 100, self.cloud, self.update_weather)
        self._slider(frame, "Rain", 0, 100, self.rain, self.update_weather)
        self._slider(frame, "Fog", 0, 100, self.fog, self.update_weather)
        self._slider(frame, "Sun Altitude", -90, 90, self.sun, self.update_time)

    def update_weather(self, *_):
        self.world.set_weather(
            WeatherParameters(
                cloudiness=self.cloud.get(),
                precipitation=self.rain.get(),
                fog_density=self.fog.get(),
            )
        )

    def update_time(self, *_):
        w = self.world.get_weather()
        w.sun_altitude_angle = self.sun.get()
        self.world.set_weather(w)

    # =================================================
    # UI HELPERS
    # =================================================
    def _entry(self, frame, label, var):
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Entry(frame, textvariable=var).pack(fill="x")

    def _slider(self, frame, label, lo, hi, var, cb):
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Scale(frame, from_=lo, to=hi, variable=var, command=cb).pack(fill="x")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        # Write a small marker to indicate UI started
        import pathlib
        marker = pathlib.Path(__file__).resolve().parent / '.ui_started'
        marker.write_text(str(time.time()))
    except Exception:
        pass

    app = CarlaUIController(root)
    try:
        root.mainloop()
    finally:
        try:
            marker = pathlib.Path(__file__).resolve().parent / '.ui_exited'
            marker.write_text(str(time.time()))
        except Exception:
            pass
