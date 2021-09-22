import subprocess
import sys
import ctypes
import threading


def install_requirements(requirements):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", requirements])

try:
    from importlib import util
    import importlib

    def module_from_file(file, module_name):
        spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, module_name)
except ImportError:
    import imp

    def module_from_file(file, module_name):
        module = imp.load_source(module_name, file)
        return getattr(module, module_name)


def parse_string_for_commands(string):
    out = []

    q = False
    ignore = False
    segment = ""

    for index, char in enumerate(string):
        if char == '"':
            if ignore:
                segment += char
                ignore = False
            else:
                if not q:
                    q = True
                else:
                    q = False
        elif char == "\\":
            if ignore:
                segment += char
                ignore = False
            else:
                ignore = True
        elif char == " ":
            if not q:
                if len(segment) > 0:
                    out.append(segment)
                segment = ""
            else:
                segment += char
            ignore = False
        else:
            segment += char
            ignore = False
    if len(segment) > 0:
        out.append(segment)

    return out


def remove_chars(string, char_list):
    return "".join([i for i in string if i not in char_list])


def ctype_async_raise(thread_obj, exception):
    found = False
    target_tid = 0
    for tid, tobj in threading._active.items():
        if tobj is thread_obj:
            found = True
            target_tid = tid
            break

    if not found:
        return False

    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.py_object(exception))
    # ref: http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    if ret == 0:
        return False
    elif ret > 1:
        # Huh? Why would we notify more than one threads?
        # Because we punch a hole into C level interpreter.
        # So it is better to clean up the mess.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, 0)
        return False
    return True
