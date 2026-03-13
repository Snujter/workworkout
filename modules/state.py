import curses
from modules.theme import Color
from modules.ui_components import SelectionPopup


class BaseState:
    """Abstract Base Class for all TUI States."""

    def __init__(self, app):
        self.app = app

    def handle_input(self, key):
        pass

    def update(self):
        pass

    def render(self, stdscr):
        pass


class MainMenuState(BaseState):
    def __init__(self, app):
        super().__init__(app)
        self.menu_items = ["Log Activity", "Change Interval", "Settings", "Exit"]
        self.current_row = 0

    def handle_input(self, key):
        if key == curses.KEY_UP:
            self.current_row = (self.current_row - 1) % len(self.menu_items)
        elif key == curses.KEY_DOWN:
            self.current_row = (self.current_row + 1) % len(self.menu_items)
        elif key in [10, 13, curses.KEY_ENTER]:
            if self.current_row == 0:  # Log Activity
                self.log_activity_flow()
            elif self.current_row == 1:  # Change Interval
                self.change_interval_flow()
            elif self.current_row == 3:  # Exit
                self.app.running = False
        elif key == 27:  # ESC
            self.app.running = False

    def log_activity_flow(self):
        popup = SelectionPopup("Select Workout", self.app.manager.workouts)
        name = popup.draw(self.app.stdscr)
        if name:
            sets = self.app.get_validated_input(f"Sets for {name}", self.app.is_positive_int, default=1)
            reps = self.app.get_validated_input(f"Reps for {name}", self.app.is_positive_int)
            self.app.manager.log_progress(name, sets, int(reps))
            self.app.save_data()

    def change_interval_flow(self):
        new_int = self.app.get_validated_input("New Interval (sec)", self.app.is_positive_int)
        if new_int:
            self.app.settings.interval_seconds = new_int
            self.app.save_data()

    def render(self, stdscr):
        h, w = stdscr.getmaxyx()
        self.app.bg_pad.erase()

        # Draw Menu
        menu_start_y = h - 7
        for idx, item in enumerate(self.menu_items):
            attr = curses.color_pair(Color.SELECTED) if idx == self.current_row else curses.A_NORMAL
            self.app.bg_pad.addstr(menu_start_y + idx, (w - 20) // 2, f" {item} ", attr)

        instructions = "ARROWS: Navigate | ENTER: Select | ESC: Exit"
        self.app.bg_pad.addstr(h - 2, (w - len(instructions)) // 2, instructions, curses.color_pair(Color.DIM))
        self.app.bg_pad.noutrefresh(0, 0, 0, 0, h - 1, w - 1)
