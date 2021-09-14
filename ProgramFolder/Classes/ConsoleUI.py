from threading import Thread
from queue import Queue, Empty
import curses
from curses import ascii
from pyperclip import paste, copy
from math import ceil


class ConsoleUI(Thread):
    def __init__(self):
        super(ConsoleUI, self).__init__()

        self.running = False
        self.setDaemon(True)
        self.queue = Queue()

        self.Screen = None
        self.Console = None
        self.Input = None

        self.max_size = 1000
        self.max_x = 0
        self.max_y = 0

        self.input_cursor = 0
        self.input_text = ""
        self.input_prefix = ""
        self.input_offset = 0

        self.input_history_cap = 50
        self.input_storage = ""
        self.input_index = -1
        self.input_history = []

        self.console_buffer = []
        self.console_display_line = 0
        self.console_line = 0
        self.newline = True

        self.select_pos = -1

    def get_input(self):
        out = []
        while self.queue.qsize() > 0:
            try:
                out.append(self.queue.get(False))
            except Empty:
                break
        return out

    def print(self, string, newline=True, loop=True):
        if not isinstance(string, type("")):
            string = string.__repr__()
        lines = string.split("\n")
        s = self.max_x

        for string in lines:
            if loop and len(string) > s:
                inputs = ceil(len(string)/s)
                for i in range(inputs):
                    self._print(string[i * s:(i+1) * s], newline=(i != (inputs - 1)) or newline)
            else:
                self._print(string, newline)

    def _print(self, string, newline=True):
        if not isinstance(string, type("")):
            string = string.__repr__()
        if not self.newline:
            self.console_line -= 1
        if self.console_line >= self.max_size - 1:
            self.hard_update_console()

        if self.newline:
            line = string
        else:
            line = self.console_buffer[-1] + string

        if self.newline:
            self.console_buffer.append(line)
        else:
            self.console_buffer[-1] = line

        if len(self.console_buffer) > self.max_size/2:
            self.console_buffer.pop(0)

        self.Console.addstr(self.console_line, 0, line[:self.max_size - 1])

        temp_display_storage = self.console_display_line
        self.set_console_scroll_pos(True)
        if temp_display_storage + 1 != self.console_display_line:
            self.console_display_line = temp_display_storage
            self.set_console_scroll_pos(False)
        self.console_line += 1
        self.refresh()

        self.newline = newline

    def get_running(self):
        return self.running

    def start(self):
        if not self.running:
            self.Screen = curses.initscr()
            curses.noecho()
            curses.cbreak()
            # self.Screen.nodelay(True)
            self.Screen.keypad(True)
            self.get_max_size()

            self.Console = curses.newpad(self.max_size, self.max_size)
            self.Input = curses.newpad(1, self.max_size)

            self.Input.move(0, 0)

            self.running = True
            super(ConsoleUI, self).start()
            self.hard_update_input()

    def stop(self):
        if self.running:
            self.running = False
            curses.nocbreak()
            self.Screen.keypad(False)
            curses.echo()
            curses.endwin()

    def run(self):
        while self.running:
            try:
                inp = self.Screen.getkey()

                if len(inp) == 1:
                    if curses.ascii.isctrl(inp):
                        if curses.ascii.isctrl(inp):
                            if inp == "\n":
                                self.push_input()
                            elif inp == "\b":
                                self.backspace()
                            elif inp == "\x16":
                                self.add_text_to_input(paste())
                            elif inp == "\x03":
                                self.copy()
                            elif inp == "\x01":
                                if len(self.input_text) > 0:
                                    self.select_pos = 0
                                    self.input_cursor = len(self.input_text)
                                self.hard_update_input()
                    elif curses.ascii.isprint(inp):
                        self.add_text_to_input(inp)
                elif inp == "KEY_LEFT":
                    self.cursor_left()
                elif inp == "KEY_RIGHT":
                    self.cursor_right()
                elif inp == "KEY_UP":
                    self.up()
                elif inp == "KEY_DOWN":
                    self.down()
                elif inp == "KEY_SLEFT":
                    self.shift_left()
                elif inp == "KEY_SRIGHT":
                    self.shift_right()
                elif inp == "KEY_SUP":
                    self.shift_up()
                elif inp == "KEY_SDOWN":
                    self.shift_down()
                elif inp == "CTL_LEFT":
                    self.input_cursor = 0
                    self.refresh(con=False)
                elif inp == "CTL_RIGHT":
                    self.input_cursor = len(self.input_text)
                    self.refresh(con=False)
                elif inp == "CTL_UP":
                    self.console_display_line = 0
                    self.refresh(inp=False)
                elif inp == "CTL_DOWN":
                    self.console_display_line = self.max_size
                    self.refresh(inp=False)
                elif inp == "KEY_RESIZE":
                    self.get_max_size()
                    self.hard_update()
            except Exception as e:
                self.stop()
                raise e

    def set_cursor_pos(self):
        self.Input.move(0, self.input_cursor + len(self.input_prefix))
        self.Screen.move(self.max_y-1, (self.input_cursor + len(self.input_prefix) - self.input_offset))

    def get_max_size(self):
        self.max_y, self.max_x = self.Screen.getmaxyx()
        self.max_x = min(self.max_x, self.max_size)
        self.max_y = min(self.max_y, self.max_size)

    def update_prefix(self, new_prefix):
        self.input_prefix = new_prefix
        max_ = self.max_size
        if (len(self.input_text) + len(self.input_prefix) + 1) > max_:
            limit = max_ - len(self.input_prefix) - 1
            self.input_text = self.input_text[:limit]
            if self.input_cursor + len(self.input_prefix) > max_ - 1:
                limit = (max_ - 1) - len(self.input_prefix)
                self.input_cursor = limit
        self.hard_update_input()

    def hard_update(self):
        self.hard_update_console()
        self.hard_update_input()

    def hard_update_console(self):
        display_line = self.console_line - self.console_display_line
        for i in range(self.max_size):
            self.Console.move(i, 0)
            self.Console.clrtoeol()
            if i < len(self.console_buffer):
                self.Console.addstr(i, 0, self.console_buffer[i][:self.max_size - 1])
        self.console_line = len(self.console_buffer)
        self.console_display_line = max(self.console_line - display_line, 0)
        self.refresh(inp=False)

    def hard_update_input(self):
        self.Input.move(0, 0)
        self.Input.clrtoeol()
        self.Input.move(0, 0)
        if self.select_pos != -1:
            a = min((self.select_pos, self.input_cursor))
            b = max((self.select_pos, self.input_cursor))
            self.Input.addstr(self.input_prefix + self.input_text[:a])
            self.Input.addstr(self.input_text[a:b], curses.A_REVERSE)
            self.Input.addstr(self.input_text[b:])
        else:
            self.Input.addstr(self.input_prefix + self.input_text)
        self.refresh(con=False)

    def refresh(self, con=True, inp=True):
        self.set_input_scroll_pos()
        self.set_console_scroll_pos()
        self.set_cursor_pos()
        if con:
            self.Console.noutrefresh(self.console_display_line, 0, 0, 0, self.max_y - 2, self.max_x - 1)
        if inp:
            self.Input.noutrefresh(0, self.input_offset, self.max_y - 1, 0, self.max_y - 1, self.max_x - 1)
        curses.doupdate()

    def add_text_to_input(self, text):
        max_ = self.max_size
        if (len(text) + len(self.input_text) + len(self.input_prefix) + 1) > max_:
            limit = max_ - len(self.input_text) - 1 - len(self.input_prefix)
            if self.select_pos != -1:
                limit += abs(self.select_pos - self.input_cursor)
            if limit <= 0:
                return
            text = text[:limit]

        if self.select_pos != -1:
            a = min((self.select_pos, self.input_cursor))
            b = max((self.select_pos, self.input_cursor))
            self.input_cursor = min(self.input_cursor, self.select_pos) + len(text)
            self.input_text = self.input_text[:a] + text + self.input_text[b:]
            self.select_pos = -1
            self.hard_update_input()
        else:
            new_segment = text + self.input_text[self.input_cursor:]
            self.input_text = self.input_text[:self.input_cursor] + new_segment
            self.Input.addstr(new_segment)
            self.input_cursor += len(text)

            self.refresh(con=False)

    def set_input_scroll_pos(self):
        if (len(self.input_prefix) + self.input_cursor) - self.input_offset > self.max_x - 1:
            self.input_offset = (len(self.input_prefix) + self.input_cursor) - (self.max_x - 1)
        if self.input_cursor - self.input_offset < 0:
            self.input_offset = self.input_cursor

    def set_console_scroll_pos(self, clamp=False):
        if not clamp:
            if self.console_display_line < (self.console_line - (self.max_size//2)):
                self.console_display_line = (self.console_line - (self.max_size//2))
            if self.console_display_line > self.console_line - (self.max_y - 1):
                self.console_display_line = self.console_line - (self.max_y - 1)
            if self.console_display_line < 0:
                self.console_display_line = 0
        else:
            if self.console_line > self.max_y - 2:
                self.console_display_line = self.console_line - (self.max_y - 2)

    def push_input(self):
        self.input_cursor = 0
        self.Input.move(0, 0)
        self.Input.clrtoeol()
        self.Input.addstr(self.input_prefix)
        self.queue.put(self.input_text)
        self.input_history.insert(0, self.input_text)
        if len(self.input_history) > self.input_history_cap:
            self.input_history = self.input_history[:self.input_history_cap]
        self.input_text = ""
        self.input_storage = ""
        self.input_index = -1
        self.select_pos = -1
        self.refresh()

    def backspace(self):
        if self.select_pos != -1:
            a = min((self.select_pos, self.input_cursor))
            b = max((self.select_pos, self.input_cursor))
            self.input_cursor = min(self.input_cursor, self.select_pos)
            self.input_text = self.input_text[:a] + self.input_text[b:]
            self.select_pos = -1
            self.hard_update_input()
            return
        if self.input_cursor == 0:
            return
        self.input_cursor -= 1
        self.set_input_scroll_pos()
        self.set_cursor_pos()
        self.input_text = self.input_text[:self.input_cursor] + self.input_text[self.input_cursor+1:]
        self.Input.delch()

        self.refresh(con=False)

    def copy(self):
        if self.select_pos == -1:
            if self.input_cursor < len(self.input_text):
                copy(self.input_text[self.input_cursor])
        else:
            a = min((self.select_pos, self.input_cursor))
            b = max((self.select_pos, self.input_cursor))
            copy(self.input_text[a:b])

    def up(self):
        if self.input_index == -1:
            self.input_storage = self.input_text
        self.input_index += 1
        if self.input_index > len(self.input_history) - 1:
            self.input_index = len(self.input_history) - 1
        self.input_text = self.input_history[self.input_index]
        self.input_cursor = len(self.input_text)
        self.Input.move(0, 0)
        self.Input.clrtoeol()
        self.Input.addstr(0, 0, self.input_prefix + self.input_text)
        self.input_offset = 0
        self.select_pos = -1
        self.refresh(con=False)

    def down(self):
        self.input_index -= 1
        if self.input_index < -1:
            self.input_index = -1
            return
        if self.input_index == -1:
            self.input_text = self.input_storage
        else:
            self.input_text = self.input_history[self.input_index]
        self.input_cursor = len(self.input_text)
        self.Input.move(0, 0)
        self.Input.clrtoeol()
        self.Input.addstr(0, 0, self.input_prefix + self.input_text)
        self.input_offset = 0
        self.select_pos = -1
        self.refresh(con=False)

    def cursor_left(self, select=False):
        if not select and self.select_pos != -1:
            self.select_pos = -1
            self.hard_update_input()
        self.input_cursor = max(self.input_cursor-1, 0)
        self.refresh(con=False)

    def cursor_right(self, select=False):
        if not select and self.select_pos != -1:
            self.select_pos = -1
            self.hard_update_input()
        self.input_cursor = min(self.input_cursor + 1, len(self.input_text))
        self.refresh(con=False)

    def shift_left(self):
        if self.select_pos == -1:
            self.select_pos = self.input_cursor
        self.cursor_left(True)
        self.set_cursor_pos()
        if self.select_pos > self.input_cursor:
            self.Input.addstr(self.input_text[self.input_cursor], curses.A_REVERSE)
        else:
            self.Input.addstr(self.input_text[self.input_cursor])
        self.refresh()

    def shift_right(self):
        if self.input_cursor == len(self.input_text):
            return
        if self.select_pos == -1:
            self.select_pos = self.input_cursor
        self.set_cursor_pos()
        if self.select_pos <= self.input_cursor:
            self.Input.addstr(self.input_text[self.input_cursor], curses.A_REVERSE)
        else:
            self.Input.addstr(self.input_text[self.input_cursor])
        self.cursor_right(True)
        self.refresh()

    def shift_up(self):
        self.console_display_line -= 1

        self.refresh(inp=False)

    def shift_down(self):
        self.console_display_line += 1

        self.refresh(inp=False)
