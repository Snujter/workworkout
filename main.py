import curses
import time
import json
import threading
import os
from datetime import datetime
from modules.models import Settings, WorkoutManager
from modules.ui_components import WorkoutTable

DATA_FILE = "workout_data.json"


class WorkoutTUI:
    # Class properties
    manager: WorkoutManager
    settings: Settings
    table: WorkoutTable
    running: bool
    last_alert_time: float
    alert_triggered: bool
    scroll_offset: int  # Added to track table position

    def __init__(self):  # Initialize state
        self.running = True
        self.last_alert_time = time.time()
        self.alert_triggered = False
        self.table = WorkoutTable()
        self.scroll_offset = 0

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

    def format_time(self, seconds):
        """Converts seconds into H:M:S format"""
        if seconds < 0: return "00h 00m 00s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}h {m:02d}m {s:02d}s"

    def background_timer(self):
        while self.running:
            elapsed = time.time() - self.last_alert_time
            threshold = self.settings.interval_minutes * 60
            if elapsed >= threshold:
                self.alert_triggered = True
                print("\a", end="", flush=True)
                self.last_alert_time = time.time()
            time.sleep(1)

    def get_input(self, stdscr, prompt):
        """Helper to get text input with a clean buffer"""
        h, w = stdscr.getmaxyx()

        # Clear the input line and show prompt
        stdscr.move(h - 2, 0)
        stdscr.clrtoeol()
        stdscr.addstr(h - 2, 2, prompt, curses.color_pair(1))

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

    def main(self, stdscr):
        # Curses Setup
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        stdscr.nodelay(True)
        stdscr.keypad(True)

        threading.Thread(target=self.background_timer, daemon=True).start()

        menu = [
            "Log Activity",
            "Manage Workouts",
            "Change Interval",
            "Exit"
        ]
        current_row = 0

        while self.running:
            stdscr.erase()
            h, w = stdscr.getmaxyx()

            # UI Header
            stdscr.addstr(1, w // 2 - 10, "WORKOUT REMINDER", curses.A_BOLD)

            # Timer Status with H/M/S Formatting
            interval_sec = self.settings.interval_minutes * 60
            time_left = int(interval_sec - (time.time() - self.last_alert_time))

            status = f"Next beep in: {self.format_time(time_left)}"
            cfg = f"Interval Set: {self.format_time(interval_sec)}"

            stdscr.addstr(3, w // 2 - len(status) // 2, status, curses.color_pair(1))
            stdscr.addstr(4, w // 2 - len(cfg) // 2, cfg)

            if self.alert_triggered:
                alert_msg = "!! TIME TO WORK OUT !! (Press 'c' to silence)"
                stdscr.addstr(6, w // 2 - len(alert_msg) // 2, alert_msg, curses.color_pair(2) | curses.A_BLINK)

            # --- Progress Table ---
            # Get history and pass it to the specific table component
            today = datetime.now().strftime("%Y-%m-%d")
            history = self.manager.history.get(today, [])

            # Title and Table are now handled entirely by this one call
            table_end_y = self.table.draw(stdscr, 6, w, history, self.scroll_offset)

            menu_start_y = table_end_y + 2

            # Render Menu (Y-offset adjusted to 9 to account for extra timer lines)
            for idx, item in enumerate(menu):
                x = w // 2 - 12
                y = menu_start_y + idx
                if idx == current_row:
                    stdscr.addstr(y, x, f" > {item} ", curses.color_pair(3))
                else:
                    stdscr.addstr(y, x, f"   {item} ")

            stdscr.refresh()

            # Input Handling
            try:
                key = stdscr.getch()
            except:
                key = -1

            if key == curses.KEY_UP:
                current_row = (current_row - 1) % len(menu)
            elif key == curses.KEY_DOWN:
                current_row = (current_row + 1) % len(menu)
            elif key == ord('c'):
                self.alert_triggered = False
            elif key in [curses.KEY_ENTER, 10, 13]:
                if current_row == 0:  # Log Activity
                    stdscr.addstr(h - 3, 2, f"Available: {', '.join(self.manager.workouts)}")
                    name = self.get_input(stdscr, "Workout Name: ")
                    if name in self.manager.workouts:
                        # Get the number of sets
                        sets_input = self.get_input(stdscr, "Sets (default 1): ")
                        sets = sets_input if sets_input else "1"
                        # Get the number of reps
                        reps = self.get_input(stdscr, "Reps per set: ")

                        if sets.isdigit() and reps.isdigit():
                            self.manager.log_progress(name, int(sets), int(reps))
                            self.save_data()
                    elif name:
                        self.get_input(stdscr, f"'{name}' not found. Press Enter...")

                elif current_row == 1:  # Manage Workouts
                    action = self.get_input(stdscr, "(A)dd or (D)elete? ").lower()
                    if action == 'a':
                        new_w = self.get_input(stdscr, "New workout name: ")
                        self.manager.add_workout_type(new_w)
                    elif action == 'd':
                        rem_w = self.get_input(stdscr, "Name to remove: ")
                        self.manager.remove_workout_type(rem_w)
                    self.save_data()

                elif current_row == 2:  # Change Interval
                    val = self.get_input(stdscr, "New interval (mins): ")
                    if val.isdigit():
                        self.settings.interval_minutes = int(val)
                        self.save_data()

                elif current_row == 3:  # Exit
                    self.running = False

            time.sleep(0.05)


if __name__ == "__main__":
    app = WorkoutTUI()
    curses.wrapper(app.main)