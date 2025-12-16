import carla
import tkinter as tk
import json
import time
import math
from pathlib import Path

# ============================================================
# CONSTANTS
# ============================================================
WINDOW_SIZE = 1200
PADDING = 40
POINT_RADIUS = 6
SIGNAL_SIZE = 6

SCENARIO_FORWARD_DISTANCE = 35.0   # meters forward from trigger
WAYPOINT_STEP = 2.0

# ============================================================
# COLORS
# ============================================================
COLOR_LANE = "#666666"
COLOR_SIGNAL = "#ff3333"

COLOR_TRIGGER = "#3366ff"
COLOR_TRIGGER_SELECTED = "#ffaa00"

COLOR_START = "red"
COLOR_GOAL = "green"
COLOR_PATH = "#00ffcc"

# ============================================================
class BEVRouteEditor:
    def __init__(self):
        # ---------------- CARLA ----------------
        self.client = carla.Client("localhost", 2000)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.map = self.world.get_map()
        print("Connected to:", self.map.name)

        self.waypoints = self.map.generate_waypoints(WAYPOINT_STEP)
        self.origin_x, self.origin_y, self.scale = self._compute_bounds_and_scale()
        self.traffic_lights = self.world.get_actors().filter("traffic.traffic_light*")

        # ---------------- SCENARIOS ----------------
        self.scenarios = self._load_scenarios()
        print(f"[BEV] Loaded {len(self.scenarios)} scenario entries")

        self.idx = 0
        self.current = self.scenarios[self.idx]

        # ---------------- UI ----------------
        self.root = tk.Tk()
        self.root.title("CARLA BEV – Scenario Browser")

        self.canvas = tk.Canvas(
            self.root, width=WINDOW_SIZE, height=WINDOW_SIZE, bg="black"
        )
        self.canvas.pack()

        self.root.bind("<Left>", self.prev_scenario)
        self.root.bind("<Right>", self.next_scenario)
        self.root.bind("<Return>", self.accept_and_save)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._redraw()
        self._print_help()
        self.root.mainloop()

    # ============================================================
    # SCENARIO LOADING
    # ============================================================
    def _load_scenarios(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "leaderboard"
            / "data"
            / "scenarios"
            / "all_towns_traffic_scenarios.json"
        )

        with open(path) as f:
            data = json.load(f)

        scenarios = []
        for town_block in data["available_scenarios"]:
            if self.map.name not in town_block:
                continue

            for scenario in town_block[self.map.name]:
                s_type = scenario["scenario_type"]
                for event in scenario["available_event_configurations"]:
                    t = event["transform"]
                    scenarios.append({
                        "scenario": s_type,
                        "x": float(t["x"]),
                        "y": float(t["y"]),
                        "z": float(t.get("z", 0.0)),
                        "yaw": float(t.get("yaw", 0.0)),
                    })
        return scenarios

    # ============================================================
    # NAVIGATION
    # ============================================================
    def next_scenario(self, *_):
        self.idx = (self.idx + 1) % len(self.scenarios)
        self.current = self.scenarios[self.idx]
        self._redraw()

    def prev_scenario(self, *_):
        self.idx = (self.idx - 1) % len(self.scenarios)
        self.current = self.scenarios[self.idx]
        self._redraw()

    # ============================================================
    # ACCEPT
    # ============================================================
    def accept_and_save(self, *_):
        print(f"[SELECTED] {self.current['scenario']}")

        start_wp = self._waypoint_from_transform(self.current)
        path = self._forward_path(start_wp, SCENARIO_FORWARD_DISTANCE)

        out = {
                "town": self.map.name,
                "intended_scenario": {
                    "scenario": self.current["scenario"],
                    "x": self.current["x"],
                    "y": self.current["y"],
                    "yaw": self.current["yaw"],
                },
                "trajectory": []
            }


        for i, wp in enumerate(path):
            loc = wp.transform.location
            out["trajectory"].append({
                "index": i,
                "x": loc.x,
                "y": loc.y,
                "z": loc.z,
                "yaw": float(wp.transform.rotation.yaw),
                "road_id": wp.road_id,
                "lane_id": wp.lane_id,
                "role": "start" if i == 0 else ("goal" if i == len(path) - 1 else "via"),
            })

        fname = f"trajectory_{int(time.time())}.json"
        with open(fname, "w") as f:
            json.dump(out, f, indent=2)

        # 🔴 CRITICAL PIPELINE HANDOFF
        marker = Path(__file__).parent / ".last_traj"
        marker.write_text(fname)

        print(f"[SAVED] {fname}")
        print(f"[PIPELINE] Trajectory marker written: {marker}")

        self.root.destroy()


    # ============================================================
    # PATH GENERATION
    # ============================================================
    def _waypoint_from_transform(self, t):
        loc = carla.Location(t["x"], t["y"], t["z"])
        return self.map.get_waypoint(loc, project_to_road=True, lane_type=carla.LaneType.Driving)

    def _forward_path(self, start_wp, distance):
        path = [start_wp]
        cur = start_wp
        traveled = 0.0

        while traveled < distance:
            nxt = cur.next(WAYPOINT_STEP)
            if not nxt:
                break
            cur = nxt[0]
            path.append(cur)
            traveled += WAYPOINT_STEP

        return path

    # ============================================================
    # DRAWING
    # ============================================================
    def _redraw(self):
        self.canvas.delete("all")
        self._draw_lanes()
        self._draw_signals()
        self._draw_triggers()
        self._draw_current_path()
        self._draw_title()

    def _draw_lanes(self):
        for w in self.waypoints:
            nxt = w.next(WAYPOINT_STEP)
            if nxt:
                self.canvas.create_line(
                    *self.world_to_screen(w.transform.location.x, w.transform.location.y),
                    *self.world_to_screen(nxt[0].transform.location.x, nxt[0].transform.location.y),
                    fill=COLOR_LANE
                )

    def _draw_signals(self):
        for tl in self.traffic_lights:
            loc = tl.get_transform().location
            sx, sy = self.world_to_screen(loc.x, loc.y)
            self.canvas.create_rectangle(
                sx - SIGNAL_SIZE, sy - SIGNAL_SIZE,
                sx + SIGNAL_SIZE, sy + SIGNAL_SIZE,
                fill=COLOR_SIGNAL
            )

    def _draw_triggers(self):
        for s in self.scenarios:
            sx, sy = self.world_to_screen(s["x"], s["y"])
            color = COLOR_TRIGGER_SELECTED if s is self.current else COLOR_TRIGGER
            self.canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill=color)

    def _draw_current_path(self):
        start_wp = self._waypoint_from_transform(self.current)
        path = self._forward_path(start_wp, SCENARIO_FORWARD_DISTANCE)

        for i in range(len(path) - 1):
            self.canvas.create_line(
                *self.world_to_screen(path[i].transform.location.x, path[i].transform.location.y),
                *self.world_to_screen(path[i+1].transform.location.x, path[i+1].transform.location.y),
                fill=COLOR_PATH,
                width=3
            )

        sx, sy = self.world_to_screen(path[0].transform.location.x, path[0].transform.location.y)
        gx, gy = self.world_to_screen(path[-1].transform.location.x, path[-1].transform.location.y)

        self.canvas.create_oval(sx-6, sy-6, sx+6, sy+6, fill=COLOR_START)
        self.canvas.create_oval(gx-6, gy-6, gx+6, gy+6, fill=COLOR_GOAL)

    def _draw_title(self):
        self.canvas.create_text(
            WINDOW_SIZE // 2, 20,
            fill="white",
            text=f"[{self.idx+1}/{len(self.scenarios)}] {self.current['scenario']}",
            font=("Helvetica", 16, "bold")
        )

    # ============================================================
    # GEOMETRY
    # ============================================================
    def _compute_bounds_and_scale(self):
        xs = [w.transform.location.x for w in self.waypoints]
        ys = [w.transform.location.y for w in self.waypoints]
        scale = min(
            (WINDOW_SIZE - PADDING) / (max(xs) - min(xs)),
            (WINDOW_SIZE - PADDING) / (max(ys) - min(ys)),
        )
        return min(xs), min(ys), scale

    def world_to_screen(self, x, y):
        sx = (x - self.origin_x) * self.scale + PADDING / 2
        sy = WINDOW_SIZE - ((y - self.origin_y) * self.scale + PADDING / 2)
        return sx, sy

    # ============================================================
    def _print_help(self):
        print("""
CONTROLS:
  ← / →   : Previous / Next scenario
  ENTER   : Accept scenario & save trajectory
  ESC     : Exit
""")


if __name__ == "__main__":
    BEVRouteEditor()
