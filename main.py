import curses
import time
import json
import os
from datetime import datetime
from modules.models import Settings, WorkoutManager
from modules.ui_components import WorkoutTable, TotalsTable, SelectionPopup, TimerWidget
from modules.theme import Color, CURSES_ESC_DELAY_TIME, CURSES_WAITING_TIME_IN_MILLISECONDS

DATA_FILE = "workout_data.json"


class WorkoutTUI:
    # Class properties
    manager: WorkoutManager
    settings: Settings
    table: WorkoutTable
    totals_table: TotalsTable
    running: bool
    last_alert_time: float
    alert_triggered: bool
    scroll_offset: int
    current_row: int
    timer_widget: TimerWidget

    def __init__(self):  # Initialize state
        os.environ.setdefault('ESCDELAY', CURSES_ESC_DELAY_TIME)

        self.running = True
        self.last_alert_time = time.time()
        self.alert_triggered = False
        self.table = WorkoutTable()
        self.totals_table = TotalsTable()
        self.timer_widget = TimerWidget()
        self.scroll_offset = 0
        self.current_row = 0

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

    def load_data(self):
        """Populates existing settings and manager objects from JSON"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    raw = json.load(f)
                    # Update existing objects instead of re-instantiating
                    if "settings" in raw:
                        self.settings.interval_seconds = raw["settings"].get("interval_seconds", 30)

                    if "workouts" in raw:
                        self.manager.workouts = raw["workouts"]

                    if "history" in raw:
                        self.manager.history = raw["history"]
            except (json.JSONDecodeError, IOError):
                # Fallback to defaults already set in __init__
                self.save_data()
        else:
            self.save_data()

    def save_data(self):
        data = {
            "settings": self.settings.to_dict(),
            **self.manager.to_dict()
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def check_timer_alerts(self):
        """Checks if the interval has elapsed and triggers audio/visual alerts."""
        elapsed = time.time() - self.last_alert_time
        threshold = self.settings.interval_seconds

        if elapsed >= threshold:
            # Trigger system beep
            print("\a", end="", flush=True)

            self.alert_triggered = True
            self.last_alert_time = time.time()

    def format_time(self, seconds):
        """Converts seconds into H:M:S format"""
        if seconds < 0: return "00h 00m 00s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}h {m:02d}m {s:02d}s"

    def get_input(self, stdscr, prompt):
        """Helper to get text input with a clean buffer"""
        h, w = stdscr.getmaxyx()

        # Clear the input line and show prompt
        stdscr.move(h - 2, 0)
        stdscr.clrtoeol()
        stdscr.addstr(h - 2, 2, prompt, curses.color_pair(Color.HEADER))

        # Preparation for input
        curses.echo()
        curses.curs_set(1)
        stdscr.nodelay(False)  # Wait for the user to actually type
        curses.flushinp()  # Clear any pending 'Enter' keys from the menu

        try:
            input_bytes = stdscr.getstr(h - 2, len(prompt) + 2)
            result = input_bytes.decode('utf-8').strip()
        except:
            result = ""

        # Cleanup after input
        curses.noecho()
        curses.curs_set(0)
        stdscr.timeout(CURSES_WAITING_TIME_IN_MILLISECONDS)
        return result

    def get_validated_input(self, stdscr, prompt, validation_func, default=None, error_pos=(0, 2)):
        """Reusable input loop with validation and error rendering."""
        error_msg = ""
        while True:
            self.render_main_ui(stdscr)
            if error_msg:
                y, x = error_pos
                stdscr.addstr(y, x, f" ERROR: {error_msg} ", curses.color_pair(Color.ALERT))

            display_prompt = f"{prompt} (default {default}): " if default else f"{prompt}: "
            val = self.get_input(stdscr, display_prompt)

            # Handle default value if input is empty
            if not val and default is not None:
                return default

            # Run validation
            is_valid, result, err = validation_func(val)
            if is_valid:
                return result

            error_msg = err

    def is_positive_int(self, val: str):
        if val.isdigit() and int(val) > 0:
            return True, int(val), ""
        return False, None, "Please enter a positive integer."

    def render_main_ui(self, stdscr):
        """Clears the screen and draws all persistent UI elements."""
        h, w = stdscr.getmaxyx()

        # Clear the Master Pad
        self.bg_pad.erase()

        # Draw non-component elements (Menu, Footer) to the Master Pad
        menu_items = ["Log Activity", "Change Interval", "Settings", "Exit"]
        menu_start_y = h - 7
        for idx, item in enumerate(menu_items):
            attr = curses.color_pair(Color.SELECTED) if idx == self.current_row else curses.A_NORMAL
            self.bg_pad.addstr(menu_start_y + idx, (w - 20) // 2, f" {item} ", attr)

        instructions = "ARROWS: Navigate | ENTER: Select | ESC: Back"
        self.bg_pad.addstr(h - 2, (w - len(instructions)) // 2, instructions, curses.color_pair(Color.DIM))

        # Refresh the Master Pad first (Bottom Layer)
        self.bg_pad.noutrefresh(0, 0, 0, 0, h - 1, w - 1)

        gap = 4
        total_combined_width = self.table.total_width + gap + self.totals_table.total_width
        start_x = max(2, (w - total_combined_width) // 2)

        # Draw Timer Pad
        self.timer_pad.erase()
        time_left = max(0, int(self.settings.interval_seconds - (time.time() - self.last_alert_time)))
        self.timer_widget.draw(self.timer_pad, self.settings.interval_seconds, time_left, total_combined_width)
        self.timer_pad.noutrefresh(0, 0, 2, start_x, 5, start_x + total_combined_width)

        # Draw History and Totals Pads
        self.workout_history_pad.erase()
        self.workout_totals_pad.erase()
        today = datetime.now().strftime("%Y-%m-%d")
        history = self.manager.history.get(today, [])

        self.table.draw(self.workout_history_pad, history)
        self.totals_table.draw(self.workout_totals_pad, history)

        log_y = 6
        self.workout_history_pad.noutrefresh(self.scroll_offset, 0, log_y, start_x, h - 8, start_x + self.table.total_width)

        totals_x = start_x + self.table.total_width + gap
        self.workout_totals_pad.noutrefresh(0, 0, log_y, totals_x, h - 8, totals_x + self.totals_table.total_width)

        # Single Physical Update
        curses.doupdate()

    def main(self, stdscr):
        # Initial Curses Setup
        curses.curs_set(0)
        curses.start_color()
        Color.setup()

        stdscr.timeout(CURSES_WAITING_TIME_IN_MILLISECONDS)

        # Define Pad sizes
        h, w = stdscr.getmaxyx()
        self.bg_pad = curses.newpad(h, w)
        self.timer_pad = curses.newpad(5, 120)
        self.workout_history_pad = curses.newpad(100, 60)
        self.workout_totals_pad = curses.newpad(100, 60)

        while self.running:
            # Draw everything
            self.render_main_ui(stdscr)

            # Check for timer alerts
            self.check_timer_alerts()

            # Wait for input
            key = stdscr.getch()

            # No key was pressed
            if key == -1:
                continue

            # Handle Navigation
            if key == curses.KEY_UP:
                self.current_row = (self.current_row - 1) % 4
            elif key == curses.KEY_DOWN:
                self.current_row = (self.current_row + 1) % 4

            # Handle Selection
            elif key in [10, 13, curses.KEY_ENTER]:
                if self.current_row == 0:  # Log Activity
                    # Show selection popup
                    popup = SelectionPopup("Select Workout", self.manager.workouts)
                    name = popup.draw(stdscr)

                    if name:
                        # Get sets
                        sets = self.get_validated_input(
                            stdscr,
                            f"Sets for {name}",
                            self.is_positive_int,
                            default=1
                        )

                        # Get reps
                        reps = self.get_validated_input(
                            stdscr,
                            f"Reps per set for {name}",
                            self.is_positive_int
                        )

                        self.manager.log_progress(name, sets, int(reps))
                        self.save_data()  # Persist changes

                elif self.current_row == 3:  # Exit
                    self.running = False

            elif key == 27:  # Global ESC to exit
                self.running = False


if __name__ == "__main__":
    app = WorkoutTUI()
    curses.wrapper(app.main)