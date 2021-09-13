import os
from functions import module_from_file
import inspect


class ControllerManager:
    commands = []
    objects = []
    file = ""

    # <editor-fold desc="Class methods">
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
    def init_commands(cls):
        cls.commands = []

        @cls.add_command(["bogos?", "bogos"])
        def binted(self, *args):
            self.console.print("binted")

        @cls.add_command(["loadcontrollers", "load_controllers"])
        def load_server_types(self, *args):
            l = len(self.get_server_names())
            self.load_server_types()
            l = len(self.get_server_names()) - l
            self.console.print(f"Loaded {l} additional controller(s) from '{self.get_server_types_dir()}'")

        @cls.add_command(["getcontrollers", "get_controllers", "printcontrollers", "print_controllers"])
        def get_server_names(self, *args):
            self.console.print(", ".join(self.get_server_names()))

        @cls.add_command(["reloadcontrollers", "reload_controllers"])
        def reload_all_controllers(self, *args):
            for i in self.get_server_names():
                self.console.print("Reloading " + i)
                self.reload_type(i)
            self.console.print("Finished Reloading all controllers")

        @cls.add_command(["reloadcontroller", "reload_controller"])
        def reload_controller(self, *args):
            if len(args) < 1:
                self.console.print("Error: Please specify a controller")
            else:
                if args[0] in self.get_server_names():
                    self.reload_type(args[0])
                    self.console.print("Reloaded " + args[0])
                else:
                    self.console.print("Error: Not a valid controller")

        @cls.add_command(["reloadmanager", "reload_manager"])
        def reload_manager(self, *args):
            self.reload()

    @classmethod
    def add_command(cls, keywords):
        def f(func):
            cls.commands.append({"keywords": keywords, "function": func})
            return func
        return f

    @classmethod
    def get_file(cls):
        if not cls.file:
            return inspect.getfile(cls)
        return cls.file

    @classmethod
    def set_file(cls, file):
        cls.file = file

    # </editor-fold>

    def __init__(self, ConsoleObj):
        self.parent_object = type(self)
        self.objects.append(self)

        self.console = ConsoleObj
        self.server_types_dir = ""
        self.server_types = {}  # format {name: {"module": module, "file": filename}}

        self.reload_needed = False

    def reload(self):
        self.reload_needed = True

    def get_reload_needed(self):
        return self.reload_needed

    def get_console(self):
        return self.console

    def remove(self):
        self.parent_object.remove(self)
        return True

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object
        self.reload_needed = False
        return True

    def run_command(self, name, *args, **kwargs):
        for i in self.parent_object.commands:
            if name.lower() in i["keywords"]:
                i["function"](self, *args, **kwargs)
                return True
        return False

    def run_command_on_server_type(self, server_type, name, *args, **kwargs):
        if server_type not in self.server_types:
            return False
        return self.server_types[server_type]["module"].run_class_command(name, *args, **kwargs)

    def run_command_on_server_instance(self, server_type, controller_name, name, *args, **kwargs):
        if server_type not in self.server_types:
            return False

    def set_server_types_dir(self, dir_):
        self.server_types_dir = dir_
        return True

    def get_server_types_dir(self):
        return self.server_types_dir

    def get_server_names(self):
        return list(self.server_types.keys())

    def load_server_types(self):
        if not self.server_types_dir:
            return False
        files = os.listdir(self.server_types_dir)
        loaded_files = [self.server_types[i]["file"] for i in self.server_types]
        for file in files:
            if file.endswith(".py"):
                if file not in loaded_files:
                    try:
                        module = module_from_file(os.path.join(self.server_types_dir, file), "Controller")
                        module.set_manager(self)
                        module.init_commands()
                        self.server_types[module.name] = {"module": module, "file": file}
                    except AttributeError:
                        pass
        return True

    def reload_type(self, name):
        if name in self.server_types:
            ty = self.server_types[name]
            file = ty["file"]
            module = ty["module"]

            obj = module.get_objects()

            try:
                new_mod = module_from_file(os.path.join(self.server_types_dir, file), "Controller")
                new_mod.set_manager(self)
                new_mod.set_objects(obj)
                new_mod.init_commands()

                del self.server_types[name]["module"]

                self.server_types[name]["module"] = new_mod
            except AttributeError:
                return False
            return True
        return False
