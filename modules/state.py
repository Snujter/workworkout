import curses
from modules.theme import Color
from modules.ui_components import SelectionPopup


class BaseState:
    """Abstract Base Class for all TUI States."""

    def __init__(self, app):
        self.app = app
        self.selection_index = 0
        self.options = []  # Child classes fill this

    def handle_input(self, key):
        """The 'Template Method' for input handling."""
        if key == curses.KEY_UP:
            self.selection_index = (self.selection_index - 1) % len(self.options)
            self.on_nav()
        elif key == curses.KEY_DOWN:
            self.selection_index = (self.selection_index + 1) % len(self.options)
            self.on_nav()
        elif key in [10, 13, curses.KEY_ENTER]:
            self.on_enter()
        elif key == 27:  # ESC
            self.on_back()

    # --- Hooks for Child Classes ---
    def on_nav(self):
        """Optional hook for sound effects or side effects on navigation."""
        pass

    def on_enter(self):
        """Required hook: What happens when Enter is pressed."""
        raise NotImplementedError

    def on_back(self):
        """Default behavior for ESC: return to previous state or exit."""
        self.app.running = False

    def render(self, stdscr):
        """Common rendering logic for menu-based states."""
        h, w = stdscr.getmaxyx()
        self.app.bg_pad.erase()

        self.draw_content(h, w)

        self.app.bg_pad.noutrefresh(0, 0, 0, 0, h - 1, w - 1)

    def draw_content(self, h, w):
        """Child classes implement the actual UI drawing here."""
        raise NotImplementedError


class MainMenuState(BaseState):
    def __init__(self, app):
        super().__init__(app)
        self.options = ["Log Activity", "Change Interval", "Settings", "Exit"]

    def on_enter(self):
        """Specific logic for the main menu."""
        if self.selection_index == 0:
            self.log_activity_flow()
        elif self.selection_index == 1:
            self.change_interval_flow()
        elif self.selection_index == 3:
            self.app.running = False

    def log_activity_flow(self):
        popup = SelectionPopup("Select Workout", self.app.manager.workouts)
        name = popup.draw(self.app.stdscr)
        if name:
            sets = self.app.get_validated_input(f"Sets for {name}", self.app.is_positive_int, default=1)
            reps = self.app.get_validated_input(f"Reps for {name}", self.app.is_positive_int)
            if sets and reps:
                self.app.manager.log_progress(name, sets, int(reps))
                self.app.save_data()

    def change_interval_flow(self):
        new_int = self.app.get_validated_input("New Interval (sec)", self.app.is_positive_int)
        if new_int:
            self.app.settings.interval_seconds = new_int
            self.app.save_data()

    def draw_content(self, h, w):
        """The child only cares about HOW the menu looks."""
        menu_start_y = h - 7
        for idx, item in enumerate(self.options):
            attr = curses.color_pair(Color.SELECTED) if idx == self.selection_index else curses.A_NORMAL
            self.app.bg_pad.addstr(menu_start_y + idx, (w - 20) // 2, f" {item} ", attr)

        instructions = "ARROWS: Navigate | ENTER: Select | ESC: Exit"
        self.app.bg_pad.addstr(h - 2, (w - len(instructions)) // 2, instructions, curses.color_pair(Color.DIM))