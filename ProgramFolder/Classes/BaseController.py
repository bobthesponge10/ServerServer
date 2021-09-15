from functions import remove_chars
from queue import Queue, Empty
import os


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
    def add_command(cls, keywords, ignore_chars=None):
        if not ignore_chars:
            ignore_chars = []

        def f(func):
            cls.commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars})
            return func

        return f

    @classmethod
    def add_class_command(cls, keywords, ignore_chars=None):
        if not ignore_chars:
            ignore_chars = []

        def f(func):
            cls.class_commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars})
            return func

        return f

    @classmethod
    def run_class_command(cls, name, handle, *args, **kwargs):
        for i in cls.class_commands:
            temp_name = remove_chars(name, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                try:
                    return i["function"](cls, handle, *args, **kwargs)
                except Exception as e:
                    handle.print(f"Error running {name}, Error: {e.__repr__()}")
                    return ""
        return ""

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
        cls.commands = []

        @cls.add_class_command(["test"])
        def test_command(cls_, user, *args):
            user.print("TestSuccess")
    # </editor-fold>

    def __init__(self, name, *args):
        self.parent_object = BaseController
        self.objects.append(self)
        self.name = name
        self.base_dir = self.manager.get_server_dir()

        self.path = os.path.join(self.base_dir, self.type, self.name)
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        self.data = None

        self.running = False

        self.queue = Queue()

    def remove(self):
        self.parent_object.remove(self)

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object

    def set_data(self, data):
        self.data = data

    def get_data(self):
        return self.data

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
                try:
                    return i["function"](self, handle, *args, **kwargs)
                except Exception as e:
                    handle.print(f"Error running {name}, Error: {e.__repr__()}")
                    return ""
        return ""

    def add_to_queue(self, item):
        self.queue.put(item, block=True, timeout=-1)

    def get_queue(self):
        out = []
        while self.queue.qsize() > 0:
            try:
                out.append(self.queue.get(False))
            except Empty:
                break
        return out

    def start(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented
