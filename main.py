import curses
import time
import json
import threading
import os
from datetime import datetime

DATA_FILE = "workout_data.json"

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
        if today not in self.history:
            self.history[today] = {}
        self.history[today][name] = self.history[today].get(name, 0) + count

    def to_dict(self):
        return {
            "workouts": self.workouts,
            "history": self.history
        }

class WorkoutTUI:
    # Class properties
    manager: WorkoutManager
    settings: Settings
    running: bool
    last_alert_time: float
    alert_triggered: bool
    scroll_offset: int  # Added to track table position

    def __init__(self):# Initialize state
        self.running = True
        self.last_alert_time = time.time()
        self.alert_triggered = False
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

    def setup_defaults(self):
        self.settings = Settings()
        self.manager = WorkoutManager()
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

        # 1. Clear the input line and show prompt
        stdscr.move(h - 2, 0)
        stdscr.clrtoeol()
        stdscr.addstr(h - 2, 2, prompt, curses.color_pair(1))

        # 2. Preparation for input
        curses.echo()
        curses.curs_set(1)
        stdscr.nodelay(False)  # Wait for the user to actually type
        curses.flushinp()  # Clear any pending 'Enter' keys from the menu

        try:
            # We use getstr and decode
            input_bytes = stdscr.getstr(h - 2, len(prompt) + 2)
            result = input_bytes.decode('utf-8').strip()
        except:
            result = ""

        # 3. Cleanup after input
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
            today = datetime.now().strftime("%Y-%m-%d")
            history = list(self.manager.history.get(today, {}).items())

            table_y = 6
            max_visible_rows = 5
            # Define exact column widths
            col1_w = 25  # Workout name
            col2_w = 10  # Reps/Count
            # Total width: 1(border) + 1(space) + col1 + 3(space|space) + col2 + 1(space) + 1(border) = 42
            table_w = col1_w + col2_w + 7
            start_x = max(0, (w - table_w) // 2)

            # Top Border
            stdscr.addstr(table_y, start_x, "┌" + "─" * (table_w - 2) + "┐")

            # Header Row - Fixed padding
            # Format: "| Workout (25) | Reps (10) |"
            header_str = f" {'Workout':<{col1_w}} │ {'Count':<{col2_w}} "
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(table_y + 1, start_x, "│" + header_str + "│")
            stdscr.attroff(curses.color_pair(1))

            if not history:
                empty_msg = "No reps yet!".center(table_w - 2)
                stdscr.addstr(table_y + 2, start_x, "│" + empty_msg + "│")
                table_end_y = table_y + 3
                visible_items = []
            else:
                visible_items = history[self.scroll_offset: self.scroll_offset + max_visible_rows]

                for i, (name, count) in enumerate(visible_items):
                    row_y = table_y + 2 + i
                    # Ensure name is truncated if too long, and count is stringified
                    clean_name = name[:col1_w]
                    row_content = f" {clean_name:<{col1_w}} │ {str(count):<{col2_w}} "
                    stdscr.addstr(row_y, start_x, "│" + row_content + "│")

                table_end_y = table_y + 2 + len(visible_items)

            # Bottom Border
            stdscr.addstr(table_end_y, start_x, "└" + "─" * (table_w - 2) + "┘")

            # Scroll indicator stays centered relative to the new table_w
            if len(history) > max_visible_rows:
                scroll_msg = f" {self.scroll_offset + 1}-{self.scroll_offset + len(visible_items)} of {len(history)} "
                stdscr.addstr(table_end_y, start_x + (table_w - len(scroll_msg)) // 2, scroll_msg, curses.A_REVERSE)

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
                        count = self.get_input(stdscr, "Amount (reps/secs): ")
                        if count.isdigit():
                            self.manager.log_progress(name, int(count))
                            self.save_data()
                            self.get_input(stdscr, "Logged! Press Enter...")
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