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

    def __init__(self):# Initialize state
        self.running = True
        self.last_alert_time = time.time()
        self.alert_triggered = False

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
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        stdscr.nodelay(True)
        stdscr.keypad(True)

        threading.Thread(target=self.background_timer, daemon=True).start()

        menu = ["Log Activity", "Manage Workouts", "View Today's Stats", "Change Interval", "Exit"]
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

            # Render Menu (Y-offset adjusted to 9 to account for extra timer lines)
            for idx, item in enumerate(menu):
                x = w // 2 - 12
                y = 9 + idx
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

                elif current_row == 2:  # Stats
                    today = datetime.now().strftime("%Y-%m-%d")
                    history = self.manager.history.get(today, {})
                    stats_str = ", ".join([f"{k}: {v}" for k, v in history.items()]) if history else "No progress yet."
                    self.get_input(stdscr, f"Today: {stats_str} (Enter to back)")

                elif current_row == 3:  # Interval
                    val = self.get_input(stdscr, "New interval (mins): ")
                    if val.isdigit():
                        self.settings.interval_minutes = int(val)
                        self.save_data()

                elif current_row == 4:  # Exit
                    self.running = False

            time.sleep(0.05)


if __name__ == "__main__":
    app = WorkoutTUI()
    curses.wrapper(app.main)