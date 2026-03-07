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
    JUNCTION_TOP = "┬"
    JUNCTION_MID = "┼"
    JUNCTION_BOT = "┴"

    def __init__(self,
                 col_widths,
                 headers,
                 title="",
                 show_title=True,
                 show_row_borders=False,
                 show_col_borders=True,
                 show_header_border=True):
        self.col_widths = col_widths
        self.headers = headers
        self.header_color_id = Color.HEADER
        self.title = title
        self.show_title = show_title
        self.show_row_borders = show_row_borders
        self.show_col_borders = show_col_borders
        self.show_header_border = show_header_border  # Store setting
        self.total_width = sum(col_widths) + (len(col_widths) * 2) + (len(col_widths) - 1) + 2

    def draw_border(self, stdscr, y, x, pos="top"):
        if pos == "top":
            left, right, junction = self.BORDER_TOP_LEFT, self.BORDER_TOP_RIGHT, self.JUNCTION_TOP
        elif pos == "mid":
            left, right, junction = self.BORDER_JOIN_LEFT, self.BORDER_JOIN_RIGHT, self.JUNCTION_MID
        else:
            left, right, junction = self.BORDER_BOT_LEFT, self.BORDER_BOT_RIGHT, self.JUNCTION_BOT

        line = left
        for i, width in enumerate(self.col_widths):
            line += self.BORDER_HORIZ * (width + 2)
            if i < len(self.col_widths) - 1:
                # Use the constant retrieved based on 'pos'
                if self.show_col_borders:
                    line += junction
                else:
                    line += self.BORDER_HORIZ
        line += right
        stdscr.addstr(y, x, line)

    def render_header_row(self, stdscr, y, x, cells, color_id):
        """Renders header where only text cells get background colors."""
        current_x = x

        # Draw Left Border
        stdscr.addstr(y, current_x, self.BORDER_SIDE)
        current_x += 1

        for i, cell in enumerate(cells):
            width = self.col_widths[i]
            content = f" {str(cell)[:width]:<{width}} "

            # Apply color ONLY to the content block
            stdscr.addstr(y, current_x, content, curses.color_pair(color_id))
            current_x += len(content)

            # Draw Divider (No background color)
            if i < len(cells) - 1:
                if self.show_col_borders:
                    stdscr.addstr(y, current_x, self.DIVIDER)
                else:
                    stdscr.addstr(y, current_x, " ")
                current_x += 1

        # Draw Right Border
        stdscr.addstr(y, current_x, self.BORDER_SIDE)

    def render_row(self, stdscr, y, x, cells, color_id=None):
        row_str = ""
        for i, cell in enumerate(cells):
            width = self.col_widths[i]
            content = str(cell)[:width]
            row_str += f" {content:<{width}} "
            if self.show_col_borders and i < len(cells) - 1:
                row_str += self.DIVIDER
            elif not self.show_col_borders and i < len(cells) - 1:
                row_str += " "

        if color_id:
            stdscr.attron(curses.color_pair(color_id))
        stdscr.addstr(y, x, f"{self.BORDER_SIDE}{row_str}{self.BORDER_SIDE}")
        if color_id:
            stdscr.attroff(curses.color_pair(color_id))

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
        self.render_header_row(stdscr, current_y, start_x, self.headers, self.header_color_id)
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
            show_title=True,
            show_row_borders=False,
            show_col_borders=False,
            show_header_border=False,
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

class Color:
    HEADER = 1
    ALERT = 2
    SELECTED = 3
    DIM = 4
    SUCCESS = 5

    @staticmethod
    def setup():
        """Initialize all color pairs in one place."""
        curses.init_pair(Color.HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(Color.ALERT, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(Color.SELECTED, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(Color.DIM, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(Color.SUCCESS, curses.COLOR_GREEN, curses.COLOR_BLACK)
