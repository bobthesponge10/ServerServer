from .functions import remove_chars
from queue import Queue, Empty
from os import path as ospath
from os import makedirs
from shutil import rmtree


class BaseController:
    commands = []
    class_commands = []
    objects = []
    manager = None
    type = "Default"

    # <editor-fold desc="Class Methods">

    @classmethod
    def get_objects(cls):
        return cls.objects

    @classmethod
    def set_objects(cls, objects):
        cls.objects = objects
        for i in cls.objects:
            i.set_parent_object(cls)

    @classmethod
    def remove_object(cls, obj):
        cls.objects.remove(obj)

    @classmethod
    def add_command(cls, keywords, ignore_chars=None, permission=0, default="", help_info=""):
        if not ignore_chars:
            ignore_chars = []
        if not default:
            default = keywords[0]

        def f(func):
            cls.commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars,
                                 "permission": permission, "default": default, "help_info": help_info})
            return func

        return f

    @classmethod
    def reset_commands(cls):
        cls.commands = []
        cls.class_commands = []

    @classmethod
    def add_class_command(cls, keywords, ignore_chars=None, permission=0, default="", help_info=""):
        if not ignore_chars:
            ignore_chars = []
        if not default:
            default = keywords[0]

        def f(func):
            cls.class_commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars,
                                       "permission": permission, "default": default, "help_info": help_info})
            return func

        return f

    @classmethod
    def find_command(cls, command, class_commands=True, instance_commands=True):
        if class_commands:
            for i in cls.class_commands:
                temp_name = remove_chars(command, i["ignore"])
                if temp_name.lower() in i["keywords"]:
                    return i
        if instance_commands:
            for i in cls.commands:
                temp_name = remove_chars(command, i["ignore"])
                if temp_name.lower() in i["keywords"]:
                    return i
        return None

    @classmethod
    def get_commands(cls, class_commands=True, instance_commands=True):
        out = []
        if class_commands:
            out += cls.class_commands
        if instance_commands:
            out += cls.commands
        return out

    @classmethod
    def run_class_command(cls, name, handle, *args, **kwargs):
        for i in cls.class_commands:
            temp_name = remove_chars(name, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                if handle.get_permissions() < i["permission"]:
                    handle.print("You don't have permission to run that command")
                    return True
                try:
                    i["function"](cls, handle, *args, **kwargs)
                    return True
                except Exception as e:
                    handle.print(f"Error running {name}, Error: {e.__repr__()}")
                    return True
        return False

    @classmethod
    def set_manager(cls, manager):
        cls.manager = manager

    @classmethod
    def get_manager(cls):
        return cls.manager
    # </editor-fold>

    # <editor-fold desc="Commands">

    @classmethod
    def init_commands(cls):

        @cls.add_class_command(["test"])
        def test_command(cls_, user, *args):
            user.print("TestSuccess")
            return True
    # </editor-fold>

    def __init__(self, name, data, port_handler, *args):
        self.parent_object = BaseController
        self.objects.append(self)
        self.name = name
        self.port_handler = port_handler
        self.base_dir = self.manager.get_server_dir()

        self.address = ""

        self.path = ospath.join(self.base_dir, self.type, self.name)
        if not ospath.isdir(self.path):
            makedirs(self.path)

        self._data = data

        self.running = False

        self.queue = Queue()

    def remove(self):
        self.parent_object.objects.remove(self)
        rmtree(self.path)
        self.port_handler.remove(delete=True)

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object

    def set_data(self, data):
        self._data = data

    def get_data(self):
        return self._data

    def get_name(self):
        return self.name

    def set_running(self, running):
        self.running = running

    def get_running(self):
        return self.running

    def run_command(self, name, handle, *args, **kwargs):
        for i in self.parent_object.commands:
            temp_name = remove_chars(name, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                if handle.get_permissions() < i["permission"]:
                    handle.print("You don't have permission to run that command")
                    return True
                try:
                    i["function"](self, handle, *args, **kwargs)
                    return True
                except Exception as e:
                    handle.print(f"Error running {name}, Error: {e.__repr__()}")
                    return True
        return False

    def add_to_queue(self, item):
        self.queue.put(f"[{self.type}/{self.name}]:{item}", block=True, timeout=-1)

    def get_queue(self):
        out = []
        while self.queue.qsize() > 0:
            try:
                out.append(self.queue.get(False))
            except Empty:
                break
        return out

    def set_address(self, address):
        self.address = address

    def get_address(self):
        return self.address

    def get_info(self):
        return ""

    def start(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def shutdown(self):
        raise NotImplemented

    def setup(self):
        pass
