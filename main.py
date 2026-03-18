import curses
import time
import json
import os
from modules.models import Settings, WorkoutManager
from modules.theme import Color, CURSES_ESC_DELAY_TIME, CURSES_WAITING_TIME_IN_MILLISECONDS
from modules.state import MainMenuState


DATA_FILE = "workout_data.json"


class WorkoutApp:
    """The State Machine Controller."""

    def __init__(self):
        os.environ.setdefault('ESCDELAY', CURSES_ESC_DELAY_TIME)
        self.running = True
        self.last_alert_time = time.time()
        self.stdscr = None

        # Define pads
        self.bg_pad = None
        self.timer_pad = None
        self.workout_history_pad = None
        self.workout_totals_pad = None

        # Initialize Data Objects (will be populated by load_data)
        self.settings = Settings()
        self.manager = WorkoutManager()

        # Load persisted data
        self.load_data()

        # State Management
        self.state = MainMenuState(self)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                raw = json.load(f)

                if "settings" in raw:
                    self.settings.interval_seconds = raw["settings"].get("interval_seconds", 30)
                if "workouts" in raw:
                    self.manager.workouts = raw["workouts"]
                if "history" in raw:
                    self.manager.history = raw["history"]

    def save_data(self):
        data = {"settings": self.settings.to_dict(), **self.manager.to_dict()}
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def is_positive_int(self, val: str):
        if str(val).isdigit() and int(val) > 0:
            return True, int(val), ""
        return False, None, "Must be a positive integer."

    def render_all(self):
        # Let the current state draw the background/menu
        self.state.render(self.stdscr)

        # Do any cleanup after render (e.g. show cursor for input if needed)
        self.state.post_render(self.stdscr)

    def main_loop(self, stdscr):
        # Initial Curses Setup
        self.stdscr = stdscr
        curses.start_color()
        Color.setup()

        stdscr.timeout(CURSES_WAITING_TIME_IN_MILLISECONDS)
        height, width = stdscr.getmaxyx()

        # Define Pad sizes
        self.bg_pad = curses.newpad(height, width)
        self.timer_pad = curses.newpad(5, 150)
        self.workout_history_pad = curses.newpad(100, 80)
        self.workout_totals_pad = curses.newpad(100, 80)

        while self.running:
            self.render_all()

            # Timer Alert Logic
            if (time.time() - self.last_alert_time) >= self.settings.interval_seconds:
                print("\a", end="", flush=True)
                self.last_alert_time = time.time()

            # Wait for input
            key = stdscr.getch()
            if key != -1:
                self.state.handle_input(key)


if __name__ == "__main__":
    app = WorkoutApp()
    curses.wrapper(app.main_loop)