import time
from datetime import datetime
import curses
from modules.theme import Color
from modules.ui_components import SelectionPopup, WorkoutTable, TotalsTable, TimerWidget


class BaseState:
    """Abstract Base Class for all TUI States."""

    def __init__(self, app):
        self.app = app
        self.selection_index = 0
        self.options = []  # Child classes fill this
        self.active_popup = None
        self.popup_index = 0
        self.popup_callback = None

    def open_popup(self, title, options, callback):
        """Helper to trigger a popup from any child state."""
        self.active_popup = SelectionPopup(title, options)
        self.popup_index = 0
        self.popup_callback = callback

    def handle_input(self, key):
        """The 'Template Method' for input handling."""
        # Popup state logic
        if self.active_popup:
            if key == curses.KEY_UP:
                self.popup_index = (self.popup_index - 1) % len(self.active_popup.options)
                self.on_popup_nav()
            elif key == curses.KEY_DOWN:
                self.popup_index = (self.popup_index + 1) % len(self.active_popup.options)
                self.on_popup_nav()
            elif key in [10, 13, curses.KEY_ENTER]:
                selection = self.active_popup.options[self.popup_index]
                callback = self.popup_callback
                self.active_popup = None  # Close before callback in case callback opens a NEW popup
                if callback:
                    callback(selection)
                self.on_popup_enter()
            elif key == 27:
                self.active_popup = None
                self.on_popup_back()
            return  # Block main state input

        # Other state logic
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

    def on_popup_nav(self):
        """Optional hook for sound effects or side effects on navigation."""
        pass

    def on_popup_enter(self):
        """Required hook: What happens when Enter is pressed."""
        pass

    def on_popup_back(self):
        """Default behavior for ESC: return to previous state or exit."""
        pass

    def render(self, stdscr):
        """Common rendering logic for menu-based states."""
        # Render background
        h, w = stdscr.getmaxyx()
        self.app.bg_pad.erase()
        self.draw_background(h, w)
        self.app.bg_pad.noutrefresh(0, 0, 0, 0, h - 1, w - 1)

        # Render content
        self.draw_content(h, w)

        # Render overlay
        if self.active_popup:
            self.draw_popup(h, w)
        else:
            self.draw_foreground(h, w)

        # Single physical update
        curses.doupdate()

    # --- Hooks for Child Classes ---
    def draw_background(self, h, w):
        """Override to add persistent UI like headers/stats to the bg_pad."""
        pass

    def draw_content(self, h, w):
        """Child classes implement the actual UI drawing here."""
        raise NotImplementedError

    def draw_foreground(self, h, w):
        """Override for UI elements that should sit above content (tooltips, etc)."""
        pass

    def draw_popup(self, h, w):
        """Popup."""
        # Re-use a dedicated popup pad from the app to avoid memory fragmentation
        p_h, p_w = self.active_popup.height, self.active_popup.width
        pop_pad = curses.newpad(p_h, p_w)
        self.active_popup.draw(pop_pad, self.popup_index)

        y = (h - p_h) // 2
        x = (w - p_w) // 2
        pop_pad.noutrefresh(0, 0, y, x, y + p_h, x + p_w)


class MainMenuState(BaseState):
    def __init__(self, app):
        super().__init__(app)
        self.options = ["Log Activity", "Change Interval", "Settings", "Exit"]

        # UI Components
        self.table = WorkoutTable()
        self.totals_table = TotalsTable()
        self.timer_widget = TimerWidget()

    def on_enter(self):
        """Specific logic for the main menu."""
        if self.selection_index == 0:
            self.log_activity_flow()
        elif self.selection_index == 1:
            self.change_interval_flow()
        elif self.selection_index == 3:
            self.app.running = False

    def log_activity_flow(self):
        # Open popup
        self.open_popup(
            title="Select Workout",
            options=self.app.manager.workouts,
            callback=self.handle_workout_select_popup
        )

    def change_interval_flow(self):
        new_int = self.app.get_validated_input("New Interval (sec)", self.app.is_positive_int)
        if new_int:
            self.app.settings.interval_seconds = new_int
            self.app.save_data()

    def handle_workout_select_popup(self, workout_name: str):
        # Exit early if no workout was selected
        if not workout_name:
            return

        # Get input for sets and reps
        sets = self.app.get_validated_input(f"Sets for {workout_name}", self.app.is_positive_int, default=1)
        reps = self.app.get_validated_input(f"Reps for {workout_name}", self.app.is_positive_int)
        if sets and reps:
            self.app.manager.log_progress(workout_name, sets, int(reps))
            self.app.save_data()

    def draw_background(self, h, w):
        # Draw menu options
        menu_start_y = h - 7
        for idx, item in enumerate(self.options):
            attr = curses.color_pair(Color.SELECTED) if idx == self.selection_index else curses.A_NORMAL
            self.app.bg_pad.addstr(menu_start_y + idx, (w - 20) // 2, f" {item} ", attr)

        # Draw menu footer
        instructions = "ARROWS: Navigate | ENTER: Select | ESC: Exit"
        self.app.bg_pad.addstr(h - 2, (w - len(instructions)) // 2, instructions, curses.color_pair(Color.DIM))

    def draw_content(self, h, w):
        """The child only cares about HOW the menu looks."""
        # Draw Global Components (Timer, Tables)
        gap = 4
        total_w = self.table.total_width + gap + self.totals_table.total_width
        start_x = max(2, (w - total_w) // 2)

        # Draw timer
        self.app.timer_pad.erase()
        elapsed = time.time() - self.app.last_alert_time
        time_left = max(0, int(self.app.settings.interval_seconds - elapsed))
        self.timer_widget.draw(self.app.timer_pad, self.app.settings.interval_seconds, time_left, total_w)
        self.app.timer_pad.noutrefresh(0, 0, 2, start_x, 5, start_x + total_w)

        # Tables
        self.app.workout_history_pad.erase()
        self.app.workout_totals_pad.erase()
        today = datetime.now().strftime("%Y-%m-%d")
        history = self.app.manager.history.get(today, [])

        self.table.draw(self.app.workout_history_pad, history)
        self.totals_table.draw(self.app.workout_totals_pad, history)

        # Refresh virtual tables
        log_y = 6
        self.app.workout_history_pad.noutrefresh(0, 0, log_y, start_x, h - 8, start_x + self.table.total_width)
        self.app.workout_totals_pad.noutrefresh(0, 0, log_y, start_x + self.table.total_width + gap, h - 8, w - 1)
