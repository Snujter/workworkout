import curses


CURSES_ESC_DELAY_TIME = '50' # the ESCDELAY setting expects a string


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
