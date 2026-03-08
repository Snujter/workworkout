import curses
import time
import json
import os
from datetime import datetime
from modules.models import Settings, WorkoutManager
from modules.ui_components import WorkoutTable, TotalsTable, SelectionPopup, TimerWidget
from modules.theme import Color, CURSES_ESC_DELAY_TIME

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
                        self.settings.interval_minutes = raw["settings"].get("interval_minutes", 30)

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
        threshold = self.settings.interval_minutes * 60

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
        stdscr.nodelay(True)  # Back to non-blocking for the timer
        return result

    def render_main_ui(self, stdscr):
        """Clears the screen and draws all persistent UI elements."""
        stdscr.erase()  # Clear the buffer
        h, w = stdscr.getmaxyx()

        # Timer Widget
        gap = 4
        total_combined_width = self.table.total_width + gap + self.totals_table.total_width
        start_x = max(2, (w - total_combined_width) // 2)
        current_y = 2
        interval_sec = self.settings.interval_minutes * 60
        time_left = int(interval_sec - (time.time() - self.last_alert_time))
        current_y = self.timer_widget.draw(
            stdscr, current_y, self.settings.interval_minutes,
            max(0, time_left), total_combined_width, start_x
        )

        # Side-by-Side Tables
        current_y += 1
        today = datetime.now().strftime("%Y-%m-%d")
        history = self.manager.history.get(today, [])

        # Draw Progress Log (Left)
        table_end_y = self.table.draw(stdscr, current_y, w, history, self.scroll_offset, x_offset=start_x)

        # Draw Totals Summary (Right)
        totals_x = start_x + self.table.total_width + gap
        self.totals_table.draw(stdscr, current_y, w, history, x_offset=totals_x)

        # Main Menu Navigation
        menu_items = ["Log Activity", "Change Interval", "Settings", "Exit"]
        menu_start_y = table_end_y + 2

        for idx, item in enumerate(menu_items):
            x_pos = (w - 20) // 2
            if idx == self.current_row:
                stdscr.addstr(menu_start_y + idx, x_pos, f" > {item} ", curses.color_pair(Color.SELECTED))
            else:
                stdscr.addstr(menu_start_y + idx, x_pos, f"   {item} ")

        # Footer Instructions
        instructions = "ARROWS: Navigate | ENTER: Select | ESC: Back"
        stdscr.addstr(h - 2, (w - len(instructions)) // 2, instructions, curses.color_pair(Color.DIM))

    def main(self, stdscr):
        # Initial Curses Setup
        curses.curs_set(0)
        curses.start_color()
        Color.setup()

        # Check every second to update timer
        stdscr.timeout(1000)

        while self.running:
            # Draw everything
            self.render_main_ui(stdscr)
            stdscr.refresh()

            # Check for timer alerts
            self.check_timer_alerts()

            # Wait for input
            key = stdscr.getch()

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
                        # Popup disappears because we re-render immediately
                        self.render_main_ui(stdscr)
                        stdscr.refresh()

                        # Prompt for sets and reps over the clean UI
                        sets_in = self.get_input(stdscr, f"Sets for {name} (default 1): ")
                        sets = int(sets_in) if sets_in.isdigit() else 1
                        reps_in = self.get_input(stdscr, "Reps per set: ")

                        if reps_in.isdigit():
                            self.manager.log_progress(name, sets, int(reps_in))
                            self.save_data()  # Persist changes

                elif self.current_row == 3:  # Exit
                    self.running = False

            elif key == 27:  # Global ESC to exit
                self.running = False


if __name__ == "__main__":
    app = WorkoutTUI()
    curses.wrapper(app.main)