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

    def __init__(self, col_widths, headers):
        self.col_widths = col_widths
        self.headers = headers
        self.total_width = sum(col_widths) + (len(col_widths) * 2) + (len(col_widths) - 1) + 2

    def draw_border(self, stdscr, y, x, pos="top"):
        left = self.BORDER_TOP_LEFT if pos == "top" else self.BORDER_BOT_LEFT
        right = self.BORDER_TOP_RIGHT if pos == "top" else self.BORDER_BOT_RIGHT
        stdscr.addstr(y, x, left + (self.BORDER_HORIZ * (self.total_width - 2)) + right)

    def render_row(self, stdscr, y, x, cells, color_pair=None):
        row_str = ""
        for i, cell in enumerate(cells):
            width = self.col_widths[i]
            content = str(cell)[:width]
            row_str += f" {content:<{width}} "
            if i < len(cells) - 1:
                row_str += self.DIVIDER

        if color_pair: stdscr.attron(color_pair)
        stdscr.addstr(y, x, f"{self.BORDER_SIDE}{row_str}{self.BORDER_SIDE}")
        if color_pair: stdscr.attroff(color_pair)

    def render(self, stdscr, y, w, data_rows, scroll_offset, max_rows):
        start_x = max(0, (w - self.total_width) // 2)
        self.draw_border(stdscr, y, start_x, "top")
        self.render_row(stdscr, y + 1, start_x, self.headers, curses.color_pair(1))

        visible_items = data_rows[scroll_offset: scroll_offset + max_rows]
        for i, row in enumerate(visible_items):
            self.render_row(stdscr, y + 2 + i, start_x, row)

        footer_y = y + 2 + len(visible_items)
        self.draw_border(stdscr, footer_y, start_x, "bot")
        return footer_y


class WorkoutTable(BaseTable):
    COL_TIME_WIDTH = 10
    COL_COUNT_WIDTH = 5
    COL_NAME_WIDTH = 20
    MAX_VISIBLE = 5

    def __init__(self):
        super().__init__(
            [self.COL_TIME_WIDTH, self.COL_COUNT_WIDTH, self.COL_NAME_WIDTH],
            ["Time", "Count", "Workout"]
        )

    def draw(self, stdscr, y, w, history_list, scroll_offset):
        rows = []
        for item in history_list:
            # Convert Unix timestamp back to local time for display
            display_time = datetime.fromtimestamp(item["timestamp"]).strftime("%H:%M:%S")

            # Add the formatted row
            rows.append([display_time, item["count"], item["name"]])

        last_y = self.render(stdscr, y, w, rows, scroll_offset, self.MAX_VISIBLE)

        if len(rows) > self.MAX_VISIBLE:
            start_x = max(0, (w - self.total_width) // 2)
            msg = f" {scroll_offset + 1}-{scroll_offset + min(len(rows), self.MAX_VISIBLE)} of {len(rows)} "
            stdscr.addstr(last_y, start_x + (self.total_width - len(msg)) // 2, msg, curses.A_REVERSE)
        return last_y
