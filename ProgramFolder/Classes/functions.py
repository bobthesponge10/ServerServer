from subprocess import check_call, CalledProcessError, PIPE
from sys import executable
from platform import system
from importlib import util, reload


def install_requirements(requirements):
    try:
        if system() == "Linux":
            check_call(["sudo", executable, "-m", "pip", "install", "-qqq", "--upgrade", "pip"], stderr=PIPE)
            check_call(["sudo", executable, "-m", "pip", "install", "-qqq", "-r", requirements], stderr=PIPE)
        else:
            check_call([executable, "-m", "pip", "install", "-q", "--upgrade", "pip"], stderr=PIPE)
            check_call([executable, "-m", "pip", "install", "-q", "-r", requirements], stderr=PIPE)
    except CalledProcessError:
        pass


def module_from_file(file, module_name):
    spec = util.spec_from_file_location(module_name, file)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, module_name)


def reload_module(module):
    return reload(module)


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
