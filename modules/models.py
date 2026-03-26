import time
import uuid
from datetime import datetime


class Settings:
    interval_seconds: int

    def __init__(self, interval_seconds=30):
        self.interval_seconds = interval_seconds

    def to_dict(self):
        return {"interval_seconds": self.interval_seconds}


class WorkoutManager:
    def __init__(self, workouts=None, history=None):
        self.workouts = workouts or [
            {"id": str(uuid.uuid4()), "name": "pushups"},
            {"id": str(uuid.uuid4()), "name": "plank"},
            {"id": str(uuid.uuid4()), "name": "squats"},
        ]
        self.history = history or {}

    def _find_workout(self, name):
        return next((w for w in self.workouts if w["name"] == name), None)

    def add_workout_type(self, name):
        if name and not self._find_workout(name):
            self.workouts.append({"id": str(uuid.uuid4()), "name": name})

    def remove_workout_type(self, name):
        workout = self._find_workout(name)
        if workout:
            self.workouts.remove(workout)

    def log_progress(self, name, sets, reps):
        workout = self._find_workout(name)
        if not workout:
            raise ValueError(f"Unknown workout: '{name}'")

        today = datetime.now().strftime("%Y-%m-%d")
        now_unix_time = time.time()

        if today not in self.history:
            self.history[today] = []

        entry = {
            "id": workout["id"],
            "name": name,
            "sets": sets,
            "reps": reps,
            "timestamp": now_unix_time
        }
        self.history[today].append(entry)

    def to_dict(self):
        return {
            "workouts": self.workouts,
            "history": self.history,
        }