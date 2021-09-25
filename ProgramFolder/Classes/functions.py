import subprocess
import sys


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

    def reload_module(module):
        return importlib.reload(module)
except ImportError:
    import imp

    def module_from_file(file, module_name):
        module = imp.load_source(module_name, file)
        return getattr(module, module_name)

    def reload_module(module):
        return imp.reload(module)


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
