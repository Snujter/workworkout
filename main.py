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
        if val.isdigit() and int(val) > 0:
            return True, int(val), ""
        return False, None, "Must be a positive integer."

    def _setup_input_mode(self):
        """Prepare curses environment for blocking user input."""
        curses.echo()
        curses.curs_set(1)
        self.stdscr.nodelay(False)

    def _restore_input_mode(self):
        """Restore curses environment to standard non-blocking mode."""
        curses.noecho()
        curses.curs_set(0)
        self.stdscr.timeout(CURSES_WAITING_TIME_IN_MILLISECONDS)

    def _draw_input_prompt(self, prompt, default, error_msg):
        """Render the input prompt line and any validation errors."""
        height, _ = self.stdscr.getmaxyx()

        if error_msg:
            self.stdscr.addstr(0, 2, f" ERROR: {error_msg} ", curses.color_pair(Color.ALERT))

        display_prompt = f"{prompt} [{default}]: " if default else f"{prompt}: "
        self.stdscr.move(height - 3, 2)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(height - 3, 2, display_prompt, curses.color_pair(Color.HEADER))

    def get_validated_input(self, prompt, validation_func, default=None):
        """Standardized blocking input with redraw."""
        self._setup_input_mode()

        result_val = None
        error_msg = ""

        while True:
            self.render_all()
            self._draw_input_prompt(prompt, default, error_msg)

            try:
                raw_input = self.stdscr.getstr().decode('utf-8').strip()

                # Check for default fallback
                if not raw_input and default is not None:
                    result_val = default
                    break

                # Validate input
                is_valid, parsed_result, err = validation_func(raw_input)
                if is_valid:
                    result_val = parsed_result
                    break

                error_msg = err
            except Exception:
                break

        self._restore_input_mode()
        return result_val

    def render_all(self):
        # Let the current state draw the background/menu
        self.state.render(self.stdscr)

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