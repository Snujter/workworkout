import time
from datetime import datetime
import curses

from modules.context import UIContextQueue, InputContext, PopupContext
from modules.theme import Color
from modules.ui_components import SelectionPopup, WorkoutTable, TotalsTable, TimerWidget, InputBox


class BaseState:
    """Abstract Base Class for all TUI States."""

    def __init__(self, app):
        self.app = app
        self.selection_index = 0
        self.options = []  # Child classes fill this
        self.ctx_queue = UIContextQueue()

    def _handle_text_input(self, ctx: InputContext, key: int):
        if key in [10, 13, curses.KEY_ENTER]:
            val = ctx.buffer.strip() or str(ctx.default or "")
            is_valid, parsed, err = ctx.validator(val)
            if is_valid:
                self.ctx_queue.resolve_active(parsed)
            else:
                ctx.error_msg = err
        elif key == 27:  # ESC - Cancel
            self.ctx_queue.clear()

        elif key in [curses.KEY_BACKSPACE, 127, 8]:
            ctx.buffer = ctx.buffer[:-1]

        elif 32 <= key <= 126:  # Printable characters
            ctx.buffer += chr(key)

    def handle_input(self, key):
        if not self.ctx_queue.active:
            self._handle_main_navigation(key)
            return

        ctx = self.ctx_queue.active

        if isinstance(ctx, InputContext):
            self._handle_text_input(ctx, key)
        elif isinstance(ctx, PopupContext):
            self._handle_popup_input(ctx, key)

    def _handle_popup_input(self, ctx: PopupContext, key: int):
        if key == curses.KEY_UP:
            ctx.index = (ctx.index - 1) % len(ctx.options)
            self.on_popup_nav()
        elif key == curses.KEY_DOWN:
            ctx.index = (ctx.index + 1) % len(ctx.options)
            self.on_popup_nav()
        elif key in [10, 13, curses.KEY_ENTER]:
            selection = ctx.options[ctx.index]
            self.ctx_queue.resolve_active(selection)
            self.on_popup_enter()
        elif key == 27:
            self.ctx_queue.clear()
            self.on_popup_back()

    def _handle_main_navigation(self, key):
        """Standard menu navigation."""
        if key == curses.KEY_UP:
            self.selection_index = (self.selection_index - 1) % len(self.options)
            self.on_nav()
        elif key == curses.KEY_DOWN:
            self.selection_index = (self.selection_index + 1) % len(self.options)
            self.on_nav()
        elif key in [10, 13, curses.KEY_ENTER]:
            self.on_enter()
        elif key == 27:
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
        ctx = self.ctx_queue.active
        if isinstance(ctx, PopupContext):
            self.draw_popup(ctx, h, w)
        elif isinstance(ctx, InputContext):
            self.draw_input_overlay(ctx, h, w)
        else:
            # Only draw foreground UI when no modal/context is blocking the view
            self.draw_foreground(h, w)

    def post_render(self, stdscr):
        ctx = self.ctx_queue.active

        if isinstance(ctx, InputContext):
            # Ensure cursor is visible
            curses.curs_set(1)

            # Move the hardware cursor to the context's coordinates
            stdscr.move(ctx.cursor_y, ctx.cursor_x)
        else:
            # Hide cursor if no input is active
            curses.curs_set(0)

        # Single physical update
        curses.doupdate()

    def draw_background(self, h, w):
        """Override to add persistent UI like headers/stats to the bg_pad."""
        pass

    def draw_content(self, h, w):
        """Child classes implement the actual UI drawing here."""
        raise NotImplementedError

    def draw_foreground(self, h, w):
        """Override for UI elements that should sit above content (tooltips, etc)."""
        pass

    def draw_popup(self, ctx: PopupContext, h, w):
        """Draws a popup from the context queue."""
        # Temporarily instantiate the UI component for rendering
        p_ui = SelectionPopup(ctx.title, ctx.options)
        p_h, p_w = p_ui.height, p_ui.width

        pop_pad = curses.newpad(p_h, p_w)
        # Use the index stored inside the context
        p_ui.draw(pop_pad, ctx.index)

        y = (h - p_h) // 2
        x = (w - p_w) // 2
        pop_pad.noutrefresh(0, 0, y, x, y + p_h, x + p_w)

    def draw_input_overlay(self, ctx: InputContext, h, w):
        # Temporarily bridge to the UI component
        input_ui = InputBox(ctx.prompt, ctx.default)
        input_ui.buffer = ctx.buffer
        input_ui.error_msg = ctx.error_msg

        input_h = 3
        input_y = h - input_h
        input_x = 2
        max_w = w - 4

        # Set the cursor position from the draw method
        ctx.cursor_y, ctx.cursor_x = input_ui.draw(self.app.bg_pad, input_y, input_x, max_w)

        # Draw directly onto the background pad or a dedicated overlay pad
        input_ui.draw(self.app.bg_pad, input_y, input_x, max_w)
        # Refresh the specific area where the input was drawn
        self.app.bg_pad.noutrefresh(input_y, 0, input_y, 0, h - 1, w - 1)


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
        """
        Defines a linear sequence of events handling logging a new activity.
        """
        # Initialize a fresh queue
        self.ctx_queue = UIContextQueue(on_complete=self._finalize_log)

        # Get the workout
        self.ctx_queue.add(PopupContext(
            title="Select Workout",
            options=self.app.manager.workouts,
            key="name"
        ))

        # Get the sets
        self.ctx_queue.add(InputContext(
            prompt="Sets",
            validator=self.app.is_positive_int,
            key="sets",
            default=1
        ))

        # Get the reps
        self.ctx_queue.add(InputContext(
            prompt="Reps",
            validator=self.app.is_positive_int,
            key="reps"
        ))

    def _finalize_log(self, data):
        """Save data to the workout log."""
        self.app.manager.log_progress(
            data["name"],
            data["sets"],
            data["reps"]
        )
        self.app.save_data()

    def change_interval_flow(self):
        # Initialize a fresh queue
        self.ctx_queue = UIContextQueue(on_complete=self._apply_interval_change)

        self.ctx_queue.add(InputContext(
            prompt="New Interval (sec)",
            validator=self.app.is_positive_int,
            key="interval"
        ))

    def _apply_interval_change(self, data):
        self.app.settings.interval_seconds = int(data['interval'])
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