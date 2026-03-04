import curses
import time
import json
import threading
import os
from datetime import datetime

DATA_FILE = "workout_data.json"


class WorkoutTUI:
    def __init__(self):
        self.load_data()
        self.running = True
        self.last_alert_time = time.time()
        self.alert_triggered = False

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    self.data = json.load(f)
            except:
                self.setup_default_data()
        else:
            self.setup_default_data()

    def setup_default_data(self):
        self.data = {
            "settings": {"interval_minutes": 30},
            "workouts": ["pushups", "plank", "squats"],
            "history": {}
        }
        self.save_data()

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def background_timer(self):
        while self.running:
            elapsed = time.time() - self.last_alert_time
            threshold = self.data["settings"]["interval_minutes"] * 60
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

            # Timer Status
            interval_sec = self.data["settings"]["interval_minutes"] * 60
            time_left = int(interval_sec - (time.time() - self.last_alert_time))
            status = f"Next beep in: {max(0, time_left)}s | Interval: {self.data['settings']['interval_minutes']}m"
            stdscr.addstr(3, w // 2 - len(status) // 2, status, curses.color_pair(1))

            if self.alert_triggered:
                alert_msg = "!! TIME TO WORK OUT !! (Press 'c' to silence)"
                stdscr.addstr(5, w // 2 - len(alert_msg) // 2, alert_msg, curses.color_pair(2) | curses.A_BLINK)

            # Render Menu
            for idx, item in enumerate(menu):
                x = w // 2 - 12
                y = 8 + idx
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
                    # Show available workouts first
                    workouts_str = f"Available: {', '.join(self.data['workouts'])}"
                    stdscr.addstr(h - 3, 2, workouts_str[:w - 4])

                    name = self.get_input(stdscr, "Workout Name: ")
                    if name in self.data["workouts"]:
                        count = self.get_input(stdscr, "Amount (reps/secs): ")
                        if count.isdigit():
                            today = datetime.now().strftime("%Y-%m-%d")
                            if today not in self.data["history"]: self.data["history"][today] = {}
                            self.data["history"][today][name] = self.data["history"][today].get(name, 0) + int(count)
                            self.save_data()
                            self.get_input(stdscr, "Logged! Press Enter...")
                    else:
                        if name:  # Only show error if they actually typed something
                            self.get_input(stdscr, f"'{name}' not found. Press Enter...")

                elif current_row == 1:  # Manage
                    action = self.get_input(stdscr, "(A)dd or (D)elete? ").lower()
                    if action == 'a':
                        new_w = self.get_input(stdscr, "New workout name: ")
                        if new_w and new_w not in self.data["workouts"]:
                            self.data["workouts"].append(new_w)
                    elif action == 'd':
                        rem_w = self.get_input(stdscr, "Name to remove: ")
                        if rem_w in self.data["workouts"]:
                            self.data["workouts"].remove(rem_w)
                    self.save_data()

                elif current_row == 2:  # Stats
                    today = datetime.now().strftime("%Y-%m-%d")
                    history = self.data["history"].get(today, {})
                    stats_str = ", ".join([f"{k}: {v}" for k, v in history.items()]) if history else "No progress yet."
                    self.get_input(stdscr, f"Today: {stats_str} (Enter to back)")

                elif current_row == 3:  # Interval
                    val = self.get_input(stdscr, "New interval (mins): ")
                    if val.isdigit():
                        self.data["settings"]["interval_minutes"] = int(val)
                        self.save_data()

                elif current_row == 4:  # Exit
                    self.running = False

            time.sleep(0.05)


if __name__ == "__main__":
    app = WorkoutTUI()
    curses.wrapper(app.main)