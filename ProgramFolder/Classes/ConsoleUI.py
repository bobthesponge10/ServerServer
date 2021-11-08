from threading import Thread
from queue import Queue, Empty
import curses
from curses import ascii
from pyperclip import paste, copy
from math import ceil
from typing import List


class ConsoleUI(Thread):
    """
    Class to handle IO from the console
    """
    def __init__(self):
        super(ConsoleUI, self).__init__()

        self._running = False
        self.setDaemon(True)
        self._queue = Queue()

        self._Screen = None
        self._Console = None
        self._Input = None

        self._max_size = 1000
        self._max_x = 0
        self._max_y = 0

        self._input_cursor = 0
        self._input_text = ""
        self._input_prefix = ""
        self._input_offset = 0

        self._input_history_cap = 50
        self._input_storage = ""
        self._input_index = -1
        self._input_history = []

        self._console_buffer = []
        self._console_display_line = 0
        self._console_line = 0
        self._newline = True

        self._select_pos = -1

        self.obscure_input = False
        self.obscure_char = "*"

    def set_obscure(self, obscure, character="*"):
        """
        Sets if the input of the user should be obscured and the character it should be obscured with.
        :param obscure: A boolean representing whether the input should be obscured.
        :param character: The character used to obscure the text with.
        """
        if not self._running:
            return
        update_needed = False

        if obscure != self.obscure_input:
            update_needed = True
        if character != self.obscure_char:
            update_needed = True

        self.obscure_input = obscure
        self.obscure_char = character

        if update_needed:
            self.hard_update_input()

    def get_input(self) -> List[str]:
        """
        Get a list of all the inputs from the user.
        :return: List of strings from the user.
        """
        out = []
        while self._queue.qsize() > 0:
            try:
                out.append(self._queue.get(False))
            except Empty:
                break
        return out

    def wait_get_input(self, timeout: float = None) -> str:
        """
        Waits till user sends input.
        :param timeout: Timeout to use
        :return: The string the user entered
        """
        return self._queue.get(True, timeout)

    def print(self, string: object, newline: bool = True, loop: bool = True):
        """
        Prints a string to the user's console. (Any code that doesn't fit will either loop or get cut)
        :param string: The string to print.
        :param newline: If a newline should be printed at the end of the string.
        :param loop: If the string should loop around if it can't fit.
        """
        if not self._running:
            return
        if not isinstance(string, type("")):
            string = string.__repr__()
        lines = string.split("\n")
        s = self._max_x

        for string in lines:
            if loop and len(string) > s:
                inputs = ceil(len(string)/s)
                for i in range(inputs):
                    self._print(string[i * s:(i+1) * s], newline=(i != (inputs - 1)) or newline)
            else:
                self._print(string, newline)

    def _print(self, string: str, newline: bool = True):
        """
        Internal function that does most of the work from printing text to the console.
        :param string: The text to print.
        :param newline: If a newline should be printed at the end of the string.
        """
        if not self._newline:
            self._console_line -= 1
        if self._console_line >= self._max_size - 1:
            self.hard_update_console()

        if self._newline:
            line = string
        else:
            line = self._console_buffer[-1] + string

        if self._newline:
            self._console_buffer.append(line)
        else:
            self._console_buffer[-1] = line

        if len(self._console_buffer) > self._max_size/2:
            self._console_buffer.pop(0)

        self._Console.addstr(self._console_line, 0, line[:self._max_size - 1])

        temp_display_storage = self._console_display_line
        self._set_console_scroll_pos(True)
        if temp_display_storage + 1 != self._console_display_line:
            self._console_display_line = temp_display_storage
            self._set_console_scroll_pos(False)
        self._console_line += 1
        self._refresh()

        self._newline = newline

    def get_running(self) -> bool:
        """
        Checks if the console is running.
        :return: True if console is running, False otherwise.
        """
        return self._running

    def start(self):
        """
        Starts the console and starts the console's thread to handle user interaction if not already running.
        """
        if not self._running:
            self._Screen = curses.initscr()
            curses.noecho()
            curses.cbreak()

            self._Screen.keypad(True)
            self._get_max_size()

            self._Console = curses.newpad(self._max_size, self._max_size)
            self._Input = curses.newpad(1, self._max_size)

            self._Input.move(0, 0)

            self._running = True
            super(ConsoleUI, self).start()
            self.hard_update_input()

    def stop(self):
        """
        Stops the console and returns IO to normal if running.
        """
        if self._running:
            self._running = False
            curses.nocbreak()
            self._Screen.keypad(False)
            curses.echo()
            curses.endwin()

    def run(self):
        """
        The method run by the seperate thread to manage user input of text and key presses.
        """
        while self._running:
            try:
                inp = self._Screen.getkey()

                if len(inp) == 1:
                    if curses.ascii.isctrl(inp):
                        if curses.ascii.isctrl(inp):
                            if inp == "\n":
                                self._push_input()
                            elif inp == "\b":
                                self._backspace()
                            elif inp == "\x16":
                                self._add_text_to_input(paste())
                            elif inp == "\x03":
                                self._copy()
                            elif inp == "\x01":
                                if len(self._input_text) > 0:
                                    self._select_pos = 0
                                    self._input_cursor = len(self._input_text)
                                self.hard_update_input()
                    elif curses.ascii.isprint(inp):
                        self._add_text_to_input(inp)
                elif inp == "KEY_LEFT":
                    self._cursor_left()
                elif inp == "KEY_RIGHT":
                    self._cursor_right()
                elif inp == "KEY_UP":
                    self._up()
                elif inp == "KEY_DOWN":
                    self._down()
                elif inp == "KEY_SLEFT":
                    self._shift_left()
                elif inp == "KEY_SRIGHT":
                    self._shift_right()
                elif inp == "KEY_SUP":
                    self._shift_up()
                elif inp == "KEY_SDOWN":
                    self._shift_down()
                elif inp == "CTL_LEFT":
                    self._input_cursor = 0
                    self._refresh(con=False)
                elif inp == "CTL_RIGHT":
                    self._input_cursor = len(self._input_text)
                    self._refresh(con=False)
                elif inp == "CTL_UP":
                    self._console_display_line = 0
                    self._refresh(inp=False)
                elif inp == "CTL_DOWN":
                    self._console_display_line = self._max_size
                    self._refresh(inp=False)
                elif inp == "KEY_RESIZE":
                    self._get_max_size()
                    self.hard_update()
            except Exception as e:
                self.stop()
                raise e

    def _set_cursor_pos(self):
        self._Input.move(0, self._input_cursor + len(self._input_prefix))
        self._Screen.move(self._max_y - 1, (self._input_cursor + len(self._input_prefix) - self._input_offset))

    def _get_max_size(self):
        self._max_y, self._max_x = self._Screen.getmaxyx()
        self._max_x = min(self._max_x, self._max_size)
        self._max_y = min(self._max_y, self._max_size)

    def update_prefix(self, new_prefix: str):
        """
        Sets the prefix of the console's input line to a given string.
        :param new_prefix: The prefix to use.
        """
        if not self._running:
            return
        self._input_prefix = new_prefix
        max_ = self._max_size
        if (len(self._input_text) + len(self._input_prefix) + 1) > max_:
            limit = max_ - len(self._input_prefix) - 1
            self._input_text = self._input_text[:limit]
            if self._input_cursor + len(self._input_prefix) > max_ - 1:
                limit = (max_ - 1) - len(self._input_prefix)
                self._input_cursor = limit
        self.hard_update_input()

    def clear_input_history(self):
        """
        Clears the console's input history.
        """
        if not self._running:
            return
        self._input_history = []
        self._input_index = -1
        self.hard_update_input()

    def clear_console(self):
        """
        Clears the console and buffer for the user.
        """
        if not self._running:
            return
        self._console_buffer = []
        self._console_line = 0
        self._console_display_line = 0
        self.hard_update_console()

    def hard_update(self):
        """
        Force redraws the entire screen.
        """
        if not self._running:
            return
        self.hard_update_console()
        self.hard_update_input()

    def hard_update_console(self):
        """
        Force redraws the output segment of the screen.
        """
        if not self._running:
            return
        display_line = self._console_line - self._console_display_line
        for i in range(self._max_size):
            self._Console.move(i, 0)
            self._Console.clrtoeol()
            if i < len(self._console_buffer):
                self._Console.addstr(i, 0, self._console_buffer[i][:self._max_size - 1])
        self._console_line = len(self._console_buffer)
        self._console_display_line = max(self._console_line - display_line, 0)
        self._refresh(inp=False)

    def hard_update_input(self):
        """
        Force redraws the input segment of the screen.
        """
        if not self._running:
            return
        self._Input.move(0, 0)
        self._Input.clrtoeol()
        self._Input.move(0, 0)
        if self._select_pos != -1:
            a = min((self._select_pos, self._input_cursor))
            b = max((self._select_pos, self._input_cursor))
            if self.obscure_input:
                self._Input.addstr(self._input_prefix + len(self._input_text[:a]) * self.obscure_char)
                self._Input.addstr(len(self._input_text[a:b]) * self.obscure_char, curses.A_REVERSE)
                self._Input.addstr(len(self._input_text[b:]) * self.obscure_char)
            else:
                self._Input.addstr(self._input_prefix + self._input_text[:a])
                self._Input.addstr(self._input_text[a:b], curses.A_REVERSE)
                self._Input.addstr(self._input_text[b:])
        else:
            if self.obscure_input:
                self._Input.addstr(self._input_prefix + len(self._input_text) * self.obscure_char)
            else:
                self._Input.addstr(self._input_prefix + self._input_text)
        self._refresh(con=False)

    def _refresh(self, con=True, inp=True):
        self._set_input_scroll_pos()
        self._set_console_scroll_pos()
        self._set_cursor_pos()
        if con:
            self._Console.noutrefresh(self._console_display_line, 0, 0, 0, self._max_y - 2, self._max_x - 1)
        if inp:
            self._Input.noutrefresh(0, self._input_offset, self._max_y - 1, 0, self._max_y - 1, self._max_x - 1)
        curses.doupdate()

    def _add_text_to_input(self, text):
        max_ = self._max_size
        if (len(text) + len(self._input_text) + len(self._input_prefix) + 1) > max_:
            limit = max_ - len(self._input_text) - 1 - len(self._input_prefix)
            if self._select_pos != -1:
                limit += abs(self._select_pos - self._input_cursor)
            if limit <= 0:
                return
            text = text[:limit]

        if self._select_pos != -1:
            a = min((self._select_pos, self._input_cursor))
            b = max((self._select_pos, self._input_cursor))
            self._input_cursor = min(self._input_cursor, self._select_pos) + len(text)
            self._input_text = self._input_text[:a] + text + self._input_text[b:]
            self._select_pos = -1
            self.hard_update_input()
        else:
            new_segment = text + self._input_text[self._input_cursor:]
            self._input_text = self._input_text[:self._input_cursor] + new_segment
            if self.obscure_input:
                self._Input.addstr(self.obscure_char)
            else:
                self._Input.addstr(new_segment)
            self._input_cursor += len(text)

            self._refresh(con=False)

    def _set_input_scroll_pos(self):
        if (len(self._input_prefix) + self._input_cursor) - self._input_offset > self._max_x - 1:
            self._input_offset = (len(self._input_prefix) + self._input_cursor) - (self._max_x - 1)
        if self._input_cursor - self._input_offset < 0:
            self._input_offset = self._input_cursor

    def _set_console_scroll_pos(self, clamp=False):
        if not clamp:
            if self._console_display_line < (self._console_line - (self._max_size // 2)):
                self._console_display_line = (self._console_line - (self._max_size // 2))
            if self._console_display_line > self._console_line - (self._max_y - 1):
                self._console_display_line = self._console_line - (self._max_y - 1)
            if self._console_display_line < 0:
                self._console_display_line = 0
        else:
            if self._console_line > self._max_y - 2:
                self._console_display_line = self._console_line - (self._max_y - 2)

    def _push_input(self):
        self._input_cursor = 0
        self._Input.move(0, 0)
        self._Input.clrtoeol()
        self._Input.addstr(self._input_prefix)
        self._queue.put(self._input_text)
        self._input_history.insert(0, self._input_text)
        if len(self._input_history) > self._input_history_cap:
            self._input_history = self._input_history[:self._input_history_cap]
        self._input_text = ""
        self._input_storage = ""
        self._input_index = -1
        self._select_pos = -1
        self._refresh()

    def _backspace(self):
        if self._select_pos != -1:
            a = min((self._select_pos, self._input_cursor))
            b = max((self._select_pos, self._input_cursor))
            self._input_cursor = min(self._input_cursor, self._select_pos)
            self._input_text = self._input_text[:a] + self._input_text[b:]
            self._select_pos = -1
            self.hard_update_input()
            return
        if self._input_cursor == 0:
            return
        self._input_cursor -= 1
        self._set_input_scroll_pos()
        self._set_cursor_pos()
        self._input_text = self._input_text[:self._input_cursor] + self._input_text[self._input_cursor + 1:]
        self._Input.delch()

        self._refresh(con=False)

    def _copy(self):
        if self._select_pos == -1:
            if self._input_cursor < len(self._input_text):
                if self.obscure_input:
                    copy(len(self._input_text[self._input_cursor]) * self.obscure_char)
                else:
                    copy(self._input_text[self._input_cursor])
        else:
            a = min((self._select_pos, self._input_cursor))
            b = max((self._select_pos, self._input_cursor))
            if self.obscure_input:
                copy(len(self._input_text[a:b]) * self.obscure_char)
            else:
                copy(self._input_text[a:b])

    def _up(self):
        if len(self._input_history) == 0:
            return
        if self._input_index == -1:
            self._input_storage = self._input_text
        self._input_index += 1
        if self._input_index > len(self._input_history) - 1:
            self._input_index = len(self._input_history) - 1
        self._input_text = self._input_history[self._input_index]
        self._input_cursor = len(self._input_text)
        self._Input.move(0, 0)
        self._Input.clrtoeol()
        if self.obscure_input:
            self._Input.addstr(0, 0, self._input_prefix + len(self._input_text) * self.obscure_char)
        else:
            self._Input.addstr(0, 0, self._input_prefix + self._input_text)
        self._input_offset = 0
        self._select_pos = -1
        self._refresh(con=False)

    def _down(self):
        self._input_index -= 1
        if self._input_index < -1:
            self._input_index = -1
            return
        if self._input_index == -1:
            self._input_text = self._input_storage
        else:
            self._input_text = self._input_history[self._input_index]
        self._input_cursor = len(self._input_text)
        self._Input.move(0, 0)
        self._Input.clrtoeol()
        if self.obscure_input:
            self._Input.addstr(0, 0, self._input_prefix + len(self._input_text) * self.obscure_char)
        else:
            self._Input.addstr(0, 0, self._input_prefix + self._input_text)
        self._input_offset = 0
        self._select_pos = -1
        self._refresh(con=False)

    def _cursor_left(self, select=False):
        if not select and self._select_pos != -1:
            self._select_pos = -1
            self.hard_update_input()
        self._input_cursor = max(self._input_cursor - 1, 0)
        self._refresh(con=False)

    def _cursor_right(self, select=False):
        if not select and self._select_pos != -1:
            self._select_pos = -1
            self.hard_update_input()
        self._input_cursor = min(self._input_cursor + 1, len(self._input_text))
        self._refresh(con=False)

    def _shift_left(self):
        if self._select_pos == -1:
            self._select_pos = self._input_cursor
        self._cursor_left(True)
        self._set_cursor_pos()
        if len(self._input_text) == 0:
            return
        if self._select_pos > self._input_cursor:
            if self.obscure_input:
                self._Input.addstr(len(self._input_text[self._input_cursor]) * self.obscure_char, curses.A_REVERSE)
            else:
                self._Input.addstr(self._input_text[self._input_cursor], curses.A_REVERSE)
        else:
            if self.obscure_input:
                self._Input.addstr(len(self._input_text[self._input_cursor]) * self.obscure_char)
            else:
                self._Input.addstr(self._input_text[self._input_cursor])
        self._refresh()

    def _shift_right(self):
        if self._input_cursor == len(self._input_text):
            return
        if self._select_pos == -1:
            self._select_pos = self._input_cursor
        self._set_cursor_pos()
        if self._select_pos <= self._input_cursor:
            if self.obscure_input:
                self._Input.addstr(len(self._input_text[self._input_cursor]) * self.obscure_char, curses.A_REVERSE)
            else:
                self._Input.addstr(self._input_text[self._input_cursor], curses.A_REVERSE)
        else:
            if self.obscure_input:
                self._Input.addstr(len(self._input_text[self._input_cursor]) * self.obscure_char)
            else:
                self._Input.addstr(self._input_text[self._input_cursor])
        self._cursor_right(True)
        self._refresh()

    def _shift_up(self):
        self._console_display_line -= 1

        self._refresh(inp=False)

    def _shift_down(self):
        self._console_display_line += 1

        self._refresh(inp=False)
