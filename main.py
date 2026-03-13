import curses
import time
import json
import os
from datetime import datetime
from modules.models import Settings, WorkoutManager
from modules.ui_components import WorkoutTable, TotalsTable, TimerWidget
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

        # UI Components
        self.table = WorkoutTable()
        self.totals_table = TotalsTable()
        self.timer_widget = TimerWidget()

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
                if "settings" in raw: self.settings.interval_seconds = raw["settings"].get("interval_seconds", 30)
                if "workouts" in raw: self.manager.workouts = raw["workouts"]
                if "history" in raw: self.manager.history = raw["history"]

    def save_data(self):
        data = {"settings": self.settings.to_dict(), **self.manager.to_dict()}
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def is_positive_int(self, val: str):
        if val.isdigit() and int(val) > 0: return True, int(val), ""
        return False, None, "Must be a positive integer."

    def get_validated_input(self, prompt, validation_func, default=None):
        """Standardized blocking input with redraw."""
        curses.echo()
        curses.curs_set(1)
        self.stdscr.nodelay(False)
        result_val = None
        error_msg = ""

        while True:
            self.render_all()
            h, w = self.stdscr.getmaxyx()
            if error_msg:
                self.stdscr.addstr(0, 2, f" ERROR: {error_msg} ", curses.color_pair(Color.ALERT))

            display_p = f"{prompt} [{default}]: " if default else f"{prompt}: "
            self.stdscr.move(h - 3, 2)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(h - 3, 2, display_p, curses.color_pair(Color.HEADER))

            try:
                raw = self.stdscr.getstr().decode('utf-8').strip()
                if not raw and default is not None:
                    result_val = default
                    break
                valid, res, err = validation_func(raw)
                if valid:
                    result_val = res
                    break
                error_msg = err
            except:
                break

        curses.noecho()
        curses.curs_set(0)
        self.stdscr.timeout(CURSES_WAITING_TIME_IN_MILLISECONDS)
        return result_val

    def render_all(self):
        h, w = self.stdscr.getmaxyx()
        # Let the current state draw the background/menu
        self.state.render(self.stdscr)

        # Draw Global Components (Timer, Tables)
        gap = 4
        total_w = self.table.total_width + gap + self.totals_table.total_width
        start_x = max(2, (w - total_w) // 2)

        # Draw timer
        self.timer_pad.erase()
        elapsed = time.time() - self.last_alert_time
        time_left = max(0, int(self.settings.interval_seconds - elapsed))
        self.timer_widget.draw(self.timer_pad, self.settings.interval_seconds, time_left, total_w)
        self.timer_pad.noutrefresh(0, 0, 2, start_x, 5, start_x + total_w)

        # Tables
        self.workout_history_pad.erase()
        self.workout_totals_pad.erase()
        today = datetime.now().strftime("%Y-%m-%d")
        history = self.manager.history.get(today, [])

        self.table.draw(self.workout_history_pad, history)
        self.totals_table.draw(self.workout_totals_pad, history)

        # Refresh virtual tables
        log_y = 6
        self.workout_history_pad.noutrefresh(0, 0, log_y, start_x, h - 8, start_x + self.table.total_width)
        self.workout_totals_pad.noutrefresh(0, 0, log_y, start_x + self.table.total_width + gap, h - 8, w - 1)

        # Single physical update
        curses.doupdate()

    def main_loop(self, stdscr):
        # Initial Curses Setup
        self.stdscr = stdscr
        curses.start_color()
        Color.setup()

        stdscr.timeout(CURSES_WAITING_TIME_IN_MILLISECONDS)

        h, w = stdscr.getmaxyx()

        # Define Pad sizes
        self.bg_pad = curses.newpad(h, w)
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