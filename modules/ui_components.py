import curses
from datetime import datetime


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

    def __init__(self, col_widths, headers, title="", show_title=True):
        self.col_widths = col_widths
        self.headers = headers
        self.title = title
        self.show_title = show_title
        self.total_width = sum(col_widths) + (len(col_widths) * 2) + (len(col_widths) - 1) + 2

    def draw_border(self, stdscr, y, x, pos="top"):
        if pos == "top":
            left, right = self.BORDER_TOP_LEFT, self.BORDER_TOP_RIGHT
        elif pos == "mid":
            left, right = self.BORDER_JOIN_LEFT, self.BORDER_JOIN_RIGHT
        else:
            left, right = self.BORDER_BOT_LEFT, self.BORDER_BOT_RIGHT

        stdscr.addstr(y, x, left + (self.BORDER_HORIZ * (self.total_width - 2)) + right)

    def render_row(self, stdscr, y, x, cells, color_pair=None):
        row_str = ""
        for i, cell in enumerate(cells):
            width = self.col_widths[i]
            content = str(cell)[:width]
            row_str += f" {content:<{width}} "
            if i < len(cells) - 1:
                row_str += self.DIVIDER

        if color_pair:
            stdscr.attron(color_pair)
        stdscr.addstr(y, x, f"{self.BORDER_SIDE}{row_str}{self.BORDER_SIDE}")
        if color_pair:
            stdscr.attroff(color_pair)

    def render(self, stdscr, y, w, data_rows, scroll_offset, max_rows):
        start_x = max(0, (w - self.total_width) // 2)
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
        self.render_row(stdscr, current_y, start_x, self.headers, curses.color_pair(1))
        current_y += 1

        # Body Section
        visible_items = data_rows[scroll_offset: scroll_offset + max_rows]
        for i, row in enumerate(visible_items):
            self.render_row(stdscr, current_y + i, start_x, row)

        # Bottom Border
        footer_y = current_y + len(visible_items)
        self.draw_border(stdscr, footer_y, start_x, "bot")

        return footer_y


class WorkoutTable(BaseTable):
    COL_TIME_WIDTH = 10
    COL_COUNT_WIDTH = 8
    COL_NAME_WIDTH = 20
    MAX_VISIBLE = 5

    def __init__(self):
        super().__init__(
            col_widths=[self.COL_TIME_WIDTH, self.COL_COUNT_WIDTH, self.COL_NAME_WIDTH],
            headers=["Time", "Count", "Workout"],
            title="TODAY'S PROGRESS",
            show_title=True
        )

    def draw(self, stdscr, y, w, history_list, scroll_offset):
        rows = []
        for item in history_list:
            # Convert Unix timestamp back to local time for display
            display_time = datetime.fromtimestamp(item["timestamp"]).strftime("%H:%M:%S")
            # Format the count column as "Sets x Reps"
            sets_x_reps = f"{item['sets']} x {item['reps']}"

            rows.append([display_time, sets_x_reps, item["name"]])

        return self.render(stdscr, y, w, rows, scroll_offset, self.MAX_VISIBLE)
