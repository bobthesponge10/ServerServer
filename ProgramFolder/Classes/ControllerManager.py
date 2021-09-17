import os
from functions import module_from_file, remove_chars
import inspect
import json
import time


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
    def add_command(cls, keywords, ignore_chars=None):
        if not ignore_chars:
            ignore_chars = []

        def f(func):
            cls.commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars})
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

    # <editor-fold desc="Commands">
    @classmethod
    def init_commands(cls):
        cls.commands = []

        ignore = ["-", "_"]

        @cls.add_command(["bogos?", "bogos"], ignore_chars=ignore)
        def binted(self, handle, *args):
            handle.print("binted")

        @cls.add_command(["loadcontrollers", "loadnewcontrollers", "newcontrollers"], ignore_chars=ignore)
        def load_server_types(self, handle, *args):
            l = len(self.get_server_names())
            self.load_server_types()
            l = len(self.get_server_names()) - l
            handle.print(f"Loaded {l} additional controller(s) from '{self.get_server_types_dir()}'")

        @cls.add_command(["getcontrollers", "printcontrollers", "listcontrollers", "controllers"], ignore_chars=ignore)
        def get_server_names(self, handle, *args):
            handle.print("\n".join([str(i[0] + 1) + ": " + i[1] for i in enumerate(self.get_server_names())]))

        @cls.add_command(["reloadcontrollers"], ignore_chars=ignore)
        def reload_all_controllers(self, handle, *args):
            for i in self.get_server_names():
                self.console.print("Reloading " + i)
                self.reload_type(i)
            handle.print("Finished Reloading all controllers")

        @cls.add_command(["reloadcontroller"], ignore_chars=ignore)
        def reload_controller(self, handle, *args):
            if len(args) < 1:
                handle.print("Error: Please specify a controller")
            else:
                if args[0] in self.get_server_names():
                    self.reload_type(args[0])
                    handle.print("Reloaded " + args[0])
                else:
                    handle.print("Error: Not a valid controller")

        @cls.add_command(["reloadmanager", "rmanager"], ignore_chars=ignore)
        def reload_manager(self, handle, *args):
            self.reload()

        @cls.add_command(["createserver", "makeserver", "createinstance", "makeinstance"], ignore_chars=ignore)
        def create_instance(self, handle, *args):
            if len(args) > 1:
                if self.create_instance(args[0], args[1], *args):
                    handle.print(f"Created instance of {args[0]} with name {args[1]}")
            handle.print("Error: invalid arguments")

        @cls.add_command(["removeinstance", "deleteinstance"], ignore_chars=ignore) # (TODO) makesure this cant happen while server is on
        def remove_instance(self, handle, *args):
            if len(args) > 1:
                if self.remove_instance(args[0], args[1]):
                    handle.print(f"Removed instance of {args[0]} with name {args[1]}")
                    return
            handle.print("Error: invalid arguments")

        @cls.add_command(["saveinstances", 'saveservers'], ignore_chars=ignore)
        def save(self, handle, *args):
            if self.save_instances_to_file():
                handle.print("Saved instances to file")
            else:
                handle.print("Failed to save instances to file")

        @cls.add_command(["loadinstances", "loadservers"], ignore_chars=ignore)
        def load(self, handle, *args):
            if self.load_instances_from_file():
                handle.print("Loaded instances from file")
            else:
                handle.print("Failed to load instances from file")

        @cls.add_command(["listinstances", "printinstances", "instances", "servers"], ignore_chars=ignore)
        def list_instances(self, handle, *args):
            out = []

            for i in self.get_server_names():
                instances = self.get_names_of_server_from_type(i)
                for name in instances:
                    out.append(f"{i}: {name}")
            if len(out) == 0:
                handle.print("No instances to list")
            else:
                handle.print("\n".join(out))

        @cls.add_command(["start"], ignore_chars=ignore)
        def start_instance(self, handle, *args):
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}")

            if m.get_running():
                handle.print(f"{args[0]}/{args[1]} is already running")
            else:
                m.start()
                handle.print(f"Starting {args[0]}/{args[1]}")

        @cls.add_command(["stop"], ignore_chars=ignore)
        def start_instance(self, handle, *args):
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}")

            if not m.get_running():
                handle.print(f"{args[0]}/{args[1]} is not running")
            else:
                m.stop()
                handle.print(f"Stopping {args[0]}/{args[1]}")

    # </editor-fold>

    def __init__(self, ConsoleObj, handle_list):
        self.parent_object = type(self)
        self.objects.append(self)

        self.console = ConsoleObj  # FOR DEBUG, remove later
        self.server_types_dir = ""
        self.server_types = {}  # format {type: {"module": module, "file": filename}}

        self.instances_data_file = ""
        self.server_dir = ""
        self.instances = {}     # format {type: [instance1, instance2, ...]}

        self.handle_list = handle_list

        self.reload_needed = False

    def reload(self):
        self.reload_needed = True

    def get_reload_needed(self):
        return self.reload_needed

    def remove(self):
        self.parent_object.remove(self)
        return True

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object
        self.reload_needed = False
        return True

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

    def run_command_on_server_type(self, server_type, name, user, *args, **kwargs):
        if server_type not in self.server_types:
            return False
        return self.server_types[server_type]["module"].run_class_command(name, user, *args, **kwargs)

    def run_command_on_server_instance(self, server_type, controller_name, name, user, *args, **kwargs):
        instance = self.get_instance_from_type_and_name(server_type, controller_name)
        if instance:
            return instance.run_command(name, user, *args, **kwargs)
        return False

    def set_server_types_dir(self, dir_):
        self.server_types_dir = dir_
        return True

    def get_server_types_dir(self):
        return self.server_types_dir

    def set_instance_data_file(self, file):
        self.instances_data_file = file

    def get_server_dir(self):
        return self.server_dir

    def set_server_dir(self, dir_):
        self.server_dir = dir_

    def get_instance_data_file(self):
        return self.instances_data_file

    def get_server_names(self):
        return list(self.server_types.keys())

    def get_names_of_server_from_type(self, type_):
        if type_ not in self.instances:
            return []
        return [i.get_name() for i in self.instances[type_]]

    def get_instance_from_type_and_name(self, type_, name):
        if type_ not in self.instances:
            return
        l = self.instances[type_]
        for i in l:
            if i.get_name() == name:
                return i

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
                        self.server_types[module.type] = {"module": module, "file": file}
                    except AttributeError:
                        pass
        self.init_instance_storage()
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

    def init_instance_storage(self):
        for i in self.get_server_names():
            if i not in self.instances:
                self.instances[i] = []

    def _create_instance_r(self, type_, name, data, *args):
        if type_ not in self.get_server_names():
            return
        if name in self.get_names_of_server_from_type(type_):
            return
        m = self.server_types[type_]["module"](name, *args)
        m.set_data(data)
        return m

    def create_instance(self, type_, name, *args):
        m = self._create_instance_r(type_, name, None, *args)
        if m:
            self.instances[type_].append(m)
            return True
        return False

    def remove_instance(self, type_, name):
        if type_ not in self.get_server_names():
            return False

        for index, instance in enumerate(self.instances[type_]):
            if instance.get_name() == name:
                del self.instances[type_][index]
                return True
        return False

    def load_instances_from_file(self):
        file = open(self.instances_data_file, "r")
        try:
            data = json.loads(file.read())
        except IOError:
            return False
        except json.decoder.JSONDecodeError:
            return False
        file.close()

        self.init_instance_storage()

        for i in data:
            l = data[i]
            for instance in l:
                ins = self._create_instance_r(i, instance["name"], instance["data"])
                if ins:
                    self.instances[i].append(ins)
        return True

    def save_instances_to_file(self):
        data = {}

        for i in self.get_server_names():
            data[i] = []

        for i in self.instances:
            l = self.instances[i]
            for instance in l:
                data[i].append({"name": instance.get_name(), "data": instance.get_data()})

        file = open(self.instances_data_file, "w")
        file.write(json.dumps(data))
        file.close()
        return True

    def print_all(self, value):
        for user in self.handle_list:
            user.print(value)

    def flush_servers(self):
        for types in self.instances:
            for instances in self.instances[types]:
                items = instances.get_queue()
                for item in items:
                    self.print_all(item)

    def close_instances(self):
        for cont in self.instances:
            for ins in self.instances[cont]:
                ins.stop()

        running = True
        while running:
            time.sleep(0.1)
            running = False
            for cont in self.instances:
                for ins in self.instances[cont]:
                    running = running or ins.get_running()