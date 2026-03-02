import time
import json
import threading
import os
import random
from datetime import datetime
from playsound3 import playsound


class WorkoutApp:
    def __init__(self, data_file="workout_data.json"):
        self.data_file = data_file
        self.running = False
        self.timer_thread = None

        # Default State
        self.state = {
            "config": {
                "interval_minutes": 30,
                "global_sounds": ["default_alert.mp3"]
            },
            "workouts": {
                "pushup": {"sounds": ["heavy_hit.mp3"], "count": 0},
                "plank": {"sounds": ["zen_bell.mp3"], "count": 0}
            },
            "history": {}
        }
        self.load_data()

    # --- Data Management ---
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.state.update(json.load(f))

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    # --- Audio Logic ---
    def _play_workout_sound(self, workout_name=None):
        """Selects a random sound from the workout's list or the global pool."""
        sound_pool = self.state["config"]["global_sounds"]

        if workout_name and workout_name in self.state["workouts"]:
            workout_sounds = self.state["workouts"][workout_name].get("sounds", [])
            if workout_sounds:
                sound_pool = workout_sounds

        if not sound_pool:
            print("\a[No sound files configured!]")
            return

        chosen_sound = random.choice(sound_pool)
        try:
            playsound(chosen_sound)
        except Exception as e:
            print(f"\n[Error playing {chosen_sound}]: {e}")

    # --- Core Reminder ---
    def reminder_loop(self):
        while self.running:
            time.sleep(self.state["config"]["interval_minutes"] * 60)
            if not self.running: break

            # Pick a random workout to suggest
            workout_name = random.choice(list(self.state["workouts"].keys()))
            print(f"\n\a[WORKOUT ALERT] Time for: {workout_name.upper()}!")
            self._play_workout_sound(workout_name)

    # --- CLI Interactions ---
    def manage_workouts(self):
        print("\n1. Add/Update Workout\n2. Delete Workout\n3. Add Sound to Workout\n4. Back")
        cmd = input("Choice: ")

        if cmd == '1':
            name = input("Workout name: ").lower()
            self.state["workouts"][name] = self.state["workouts"].get(name, {"sounds": [], "count": 0})
            print(f"Added/Updated {name}.")
        elif cmd == '2':
            name = input("Name to delete: ").lower()
            self.state["workouts"].pop(name, None)
        elif cmd == '3':
            name = input("Workout name: ").lower()
            if name in self.state["workouts"]:
                sound_path = input("Path to sound file: ")
                self.state["workouts"][name]["sounds"].append(sound_path)
            else:
                print("Workout not found.")
        self.save_data()

    def run(self):
        while True:
            status = "RUNNING" if self.running else "STOPPED"
            print(f"\n--- GYM-IN-CLI [{status}] ---")
            print(f"Interval: {self.state['config']['interval_minutes']}m")
            print("1. Toggle Timer | 2. Manage Workouts | 3. Set Interval | 4. Progress | 5. Exit")

            choice = input(">> ")

            if choice == '1':
                self.running = not self.running
                if self.running:
                    self.timer_thread = threading.Thread(target=self.reminder_loop, daemon=True)
                    self.timer_thread.start()
            elif choice == '2':
                self.manage_workouts()
            elif choice == '3':
                self.state["config"]["interval_minutes"] = int(input("Minutes: "))
                self.save_data()
            elif choice == '4':
                print(json.dumps(self.state["history"], indent=2))
            elif choice == '5':
                self.running = False
                break


if __name__ == "__main__":
    app = WorkoutApp()
    app.run()