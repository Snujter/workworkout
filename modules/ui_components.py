import curses
from datetime import datetime
from modules.theme import Color


class TimerWidget:
    def __init__(self):
        self.height = 3
        self.BAR_FILLED = "█"
        self.BAR_EMPTY = "░"

    def draw(self, stdscr, y, interval_seconds, seconds_left, width, start_x):
        """Draws the progress bar at the specified y coordinate."""
        # Calculate percentage: (Time Remaining / Total Time)
        total_seconds = max(1, interval_seconds)
        percent = max(0, min(1, seconds_left / total_seconds))

        usable_width = width - 2
        filled_length = int(usable_width * percent)

        # Format the overlay text
        hours, remainder = divmod(seconds_left, 3600)
        mins, secs = divmod(remainder, 60)
        if hours > 0:
            time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
        else:
            time_str = f"{mins:02d}:{secs:02d}"

        # Add padding to the text for better spacing
        time_str = f" {time_str} "
        text_start_in_bar = (usable_width - len(time_str)) // 2

        # Draw the Box Border
        stdscr.attron(curses.color_pair(Color.DIM))
        stdscr.addch(y, start_x, curses.ACS_ULCORNER)
        stdscr.addch(y, start_x + width - 1, curses.ACS_URCORNER)
        stdscr.addch(y + 2, start_x, curses.ACS_LLCORNER)
        stdscr.addch(y + 2, start_x + width - 1, curses.ACS_LRCORNER)
        stdscr.hline(y, start_x + 1, curses.ACS_HLINE, usable_width)
        stdscr.hline(y + 2, start_x + 1, curses.ACS_HLINE, usable_width)
        stdscr.addch(y + 1, start_x, curses.ACS_VLINE)
        stdscr.addch(y + 1, start_x + width - 1, curses.ACS_VLINE)
        stdscr.attroff(curses.color_pair(Color.DIM))

        # Render the bar and text character by character
        for i in range(usable_width):
            is_text_zone = text_start_in_bar <= i < text_start_in_bar + len(time_str)

            if is_text_zone:
                char_to_draw = time_str[i - text_start_in_bar]
                # Inverse color if text is over the filled portion
                attr = curses.A_REVERSE | curses.A_BOLD if i < filled_length else curses.A_BOLD
            else:
                char_to_draw = self.BAR_FILLED if i < filled_length else self.BAR_EMPTY
                attr = curses.A_NORMAL

            stdscr.addch(y + 1, start_x + 1 + i, char_to_draw, attr)

        return y + self.height


class BaseTable:
    BORDER_TOP_LEFT = "┌"
    BORDER_TOP_RIGHT = "┐"
    BORDER_BOT_LEFT = "└"
    BORDER_BOT_RIGHT = "┘"
    BORDER_SIDE = "│"
    BORDER_HORIZ = "─"
    DIVIDER = "│"
    BORDER_JOIN_LEFT = "├"
    BORDER_JOIN_RIGHT = "┤"
    JUNCTION_TOP = "┬"
    JUNCTION_MID = "┼"
    JUNCTION_BOT = "┴"

    def __init__(self,
                 headers,
                 title="",
                 show_title=True,
                 show_row_borders=False,
                 show_col_borders=True,
                 show_header_border=True):
        self.headers = headers  # List of dicts: {"title": str, "width": int, "align": str}
        self.header_color_id = Color.HEADER
        self.title = title
        self.show_title = show_title
        self.show_row_borders = show_row_borders
        self.show_col_borders = show_col_borders
        self.show_header_border = show_header_border  # Store setting
        self.total_width = sum(h["width"] for h in headers) + (len(headers) * 2) + (len(headers) - 1) + 2

    def draw_border(self, stdscr, y, x, pos="top"):
        # Set dividers
        if pos == "top":
            left, right, junction = self.BORDER_TOP_LEFT, self.BORDER_TOP_RIGHT, self.JUNCTION_TOP
        elif pos == "mid":
            left, right, junction = self.BORDER_JOIN_LEFT, self.BORDER_JOIN_RIGHT, self.JUNCTION_MID
        else:
            left, right, junction = self.BORDER_BOT_LEFT, self.BORDER_BOT_RIGHT, self.JUNCTION_BOT

        # Set up line
        line = left

        # Iterating through the header objects
        for i, h_cfg in enumerate(self.headers):
            # Each column width + 2 for the internal padding spaces
            line += self.BORDER_HORIZ * (h_cfg["width"] + 2)

            if i < len(self.headers) - 1:
                if self.show_col_borders:
                    line += junction
                else:
                    line += self.BORDER_HORIZ

        line += right
        stdscr.addstr(y, x, line)

    def render_header_row(self, stdscr, y, x, color_id):
        """Renders header where only text cells get background colors."""
        current_x = x

        # Draw Left Border
        stdscr.addstr(y, current_x, self.BORDER_SIDE)
        current_x += 1

        for i, h_cfg in enumerate(self.headers):
            content = self._format_cell(h_cfg["title"], h_cfg)

            # Apply color ONLY to the content block
            stdscr.addstr(y, current_x, content, curses.color_pair(color_id))
            current_x += len(content)

            # Draw Divider (No background color)
            if i < len(self.headers) - 1:
                stdscr.addstr(y, current_x, self.DIVIDER if self.show_col_borders else " ")
                current_x += 1

        # Draw Right Border
        stdscr.addstr(y, current_x, self.BORDER_SIDE)

    def render_row(self, stdscr, y, x, cells, color_id=None):
        current_x = x
        stdscr.addstr(y, current_x, self.BORDER_SIDE)
        current_x += 1

        for i, cell in enumerate(cells):
            content = self._format_cell(cell, self.headers[i])

            if color_id:
                stdscr.attron(curses.color_pair(color_id))
            stdscr.addstr(y, current_x, content)
            if color_id:
                stdscr.attroff(curses.color_pair(color_id))

            current_x += len(content)

            if i < len(self.headers) - 1:
                stdscr.addstr(y, current_x, self.DIVIDER if self.show_col_borders else " ")
                current_x += 1

        stdscr.addstr(y, current_x, self.BORDER_SIDE)

    def render(self, stdscr, y, w, data_rows, scroll_offset, max_rows, x_offset=None):
        # If x_offset is provided, use it; otherwise, center the table
        start_x = x_offset if x_offset is not None else max(0, (w - self.total_width) // 2)
        current_y = y

        # Bordered Title Section
        if self.show_title and self.title:
            self.draw_border(stdscr, current_y, start_x, "top")
            title_padded = self.title.center(self.total_width - 2)
            stdscr.addstr(current_y + 1, start_x, f"{self.BORDER_SIDE}{title_padded}{self.BORDER_SIDE}", curses.A_BOLD)
            current_y += 2
            self.draw_border(stdscr, current_y, start_x, "mid")
        else:
            self.draw_border(stdscr, current_y, start_x, "top")

        current_y += 1

        # Header Row
        self.render_header_row(stdscr, current_y, start_x, self.header_color_id)
        current_y += 1

        # Conditional Header Bottom Border
        if self.show_header_border:
            self.draw_border(stdscr, current_y, start_x, "mid")
            current_y += 1

        # Body Section
        visible_items = data_rows[scroll_offset: scroll_offset + max_rows]
        for i, row in enumerate(visible_items):
            if self.show_row_borders and i > 0:
                self.draw_border(stdscr, current_y, start_x, "mid")
                current_y += 1
            self.render_row(stdscr, current_y, start_x, row)
            current_y += 1

        # Bottom Border
        self.draw_border(stdscr, current_y, start_x, "bot")

        return current_y

    def _format_cell(self, text, header_cfg):
        """Uses the header object to determine padding and alignment."""
        width = header_cfg["width"]
        align = header_cfg.get("align", "left")
        text = str(text)[:width]

        if align == "center":
            return f" {text.center(width)} "
        elif align == "right":
            return f" {text.rjust(width)} "
        else:
            return f" {text.ljust(width)} "

class WorkoutTable(BaseTable):
    MAX_VISIBLE = 5

    def __init__(self):
        headers = [
            {"title": "Time", "width": 5, "align": "right"},
            {"title": "Reps", "width": 7, "align": "right"},
            {"title": "Workout", "width": 20, "align": "left"}
        ]

        super().__init__(
            headers=headers,
            title="TODAY'S PROGRESS",
            show_title=True,
            show_row_borders=False,
            show_col_borders=False,
            show_header_border=False,
        )

    def draw(self, stdscr, y, w, history_list, scroll_offset, x_offset):
        rows = []
        for item in history_list:
            # Convert Unix timestamp back to local time for display
            display_time = datetime.fromtimestamp(item["timestamp"]).strftime("%H:%M")
            # Format the count column as "Sets x Reps"
            sets_x_reps = f"{item['sets']} x {item['reps']}"

            rows.append([display_time, sets_x_reps, item["name"]])

        return self.render(stdscr, y, w, rows, scroll_offset, self.MAX_VISIBLE, x_offset=x_offset)

class TotalsTable(BaseTable):
    MAX_VISIBLE = 8

    def __init__(self):
        headers = [
            {"title": "Reps", "width": 4, "align": "right"},
            {"title": "Workout", "width": 20, "align": "left"},
        ]
        super().__init__(
            headers=headers,
            title="DAILY TOTALS",
            show_title=True,
            show_row_borders=False,
            show_col_borders=False,
            show_header_border=False,
        )

    def draw(self, stdscr, y, w, history_list, x_offset):
        # Aggregate totals from the history list of dictionaries
        totals = {}
        for item in history_list:
            name = item["name"]
            # Volume = sets * reps
            volume = item["sets"] * item["reps"]
            totals[name] = totals.get(name, 0) + volume

        rows = [[count, name] for name, count in totals.items()]
        # Render with the specific x_offset
        return self.render(stdscr, y, w, rows, 0, self.MAX_VISIBLE, x_offset=x_offset)


class SelectionPopup:
    def __init__(self, title, options):
        self.title = title
        self.options = options
        self.selected_idx = 0

    def draw(self, stdscr):
        h, w = stdscr.getmaxyx()
        popup_h = len(self.options) + 5
        popup_w = max(len(self.title), max(len(o) for o in self.options)) + 8
        start_y = (h - popup_h) // 2
        start_x = (w - popup_w) // 2

        while True:
            # Draw Background
            for i in range(popup_h):
                stdscr.addstr(start_y + i, start_x, " " * popup_w, curses.color_pair(Color.HEADER))

            # Draw Box Borders
            stdscr.attron(curses.color_pair(Color.HEADER))
            stdscr.addch(start_y, start_x, curses.ACS_ULCORNER)
            stdscr.addch(start_y, start_x + popup_w - 1, curses.ACS_URCORNER)
            stdscr.addch(start_y + popup_h - 1, start_x, curses.ACS_LLCORNER)
            stdscr.addch(start_y + popup_h - 1, start_x + popup_w - 1, curses.ACS_LRCORNER)
            stdscr.hline(start_y, start_x + 1, curses.ACS_HLINE, popup_w - 2)
            stdscr.hline(start_y + popup_h - 1, start_x + 1, curses.ACS_HLINE, popup_w - 2)
            stdscr.vline(start_y + 1, start_x, curses.ACS_VLINE, popup_h - 2)
            stdscr.vline(start_y + 1, start_x + popup_w - 1, curses.ACS_VLINE, popup_h - 2)

            stdscr.addstr(start_y + 1, start_x + (popup_w - len(self.title)) // 2, self.title, curses.A_BOLD)
            stdscr.attroff(curses.color_pair(Color.HEADER))

            # Render Options
            for idx, option in enumerate(self.options):
                attr = curses.color_pair(Color.SELECTED) if idx == self.selected_idx else curses.color_pair(
                    Color.HEADER)
                line = f" {option} ".center(popup_w - 2)
                stdscr.addstr(start_y + 3 + idx, start_x + 1, line, attr)

            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                self.selected_idx = (self.selected_idx - 1) % len(self.options)
            elif key == curses.KEY_DOWN:
                self.selected_idx = (self.selected_idx + 1) % len(self.options)
            elif key in [10, 13, curses.KEY_ENTER]:
                return self.options[self.selected_idx]
            elif key == 27:  # ESC
                return None
