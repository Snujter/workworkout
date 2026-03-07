import time
from datetime import datetime

class Settings:
    def __init__(self, interval_minutes=30):
        self.interval_minutes = interval_minutes

    def to_dict(self):
        return {"interval_minutes": self.interval_minutes}

class WorkoutManager:
    def __init__(self, workouts=None, history=None):
        self.workouts = workouts or ["pushups", "plank", "squats"]
        self.history = history or {}

    def add_workout_type(self, name):
        if name and name not in self.workouts:
            self.workouts.append(name)

    def remove_workout_type(self, name):
        if name in self.workouts:
            self.workouts.remove(name)

    def log_progress(self, name, count):
        today = datetime.now().strftime("%Y-%m-%d")
        now_unix_time = time.time()

        if today not in self.history:
            self.history[today] = []

        entry = {
            "name": name,
            "count": count,
            "timestamp": now_unix_time
        }
        self.history[today].append(entry)

    def to_dict(self):
        return {
            "workouts": self.workouts,
            "history": self.history
        }