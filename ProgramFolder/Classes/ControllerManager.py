from os import path as ospath
from os import listdir
from .functions import module_from_file, remove_chars
from .EnvManager import EnvManager
from inspect import getfile
from json import loads, dumps, decoder
from time import sleep
from sys import version


class ControllerManager:
    commands = []
    objects = []
    file = ""

    # <editor-fold desc="Class/Static methods">
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
    def add_command(cls, keywords, ignore_chars=None, global_function=False, permission=0, default="", help_info=""):
        if not ignore_chars:
            ignore_chars = []

        if not default:
            default = keywords[0]

        def f(func):
            cls.commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars,
                                 "global": global_function, "permission": permission, "default": default,
                                 "help_info": help_info})
            return func

        return f

    @classmethod
    def find_command(cls, command, global_func=False):
        for i in cls.commands:
            temp_name = remove_chars(command, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                if not (global_func and not i["global"]):
                    return i
        return None

    @classmethod
    def get_commands(cls, global_func=True):
        return [i for i in cls.commands if not global_func or i["global"]]

    @classmethod
    def get_file(cls):
        if not cls.file:
            return getfile(cls)
        return cls.file

    @classmethod
    def set_file(cls, file):
        cls.file = file

    @staticmethod
    def join_args(args_a, args_b):
        out = []
        for i in args_b:
            if i:
                out.append(i)
        for i in args_a:
            if i:
                out.append(i)
        return out
    # </editor-fold>

    # <editor-fold desc="Commands">
    @classmethod
    def init_commands(cls):
        cls.commands = []

        ignore = ["-", "_", " "]

        @cls.add_command(["debug"], global_function=True)
        def debug_function(self, handle, *args, **kwargs):
            handle.print("test")
            for user in self.handle_list:
                handle.print("-----")
                handle.print(user.get_username())
                handle.print(user.id)
                handle.print(user.obj)
                handle.print(user.server)

        @cls.add_command(["status"], ignore_chars=ignore, global_function=True,
                         help_info="Displays some basic info on the status of the server server.")
        def status(self, handle, *args, **kwargs):
            handle.print("\n".join(self.get_status()))

        @cls.add_command(["help", "h"], ignore_chars=ignore, global_function=True, default="help",
                         help_info="Use this command to find out how to use a command. Ex: help <command>")
        def help(self, handle, *args, controller="", instance="", **kwargs):
            if len(args) < 1:
                handle.print("Use this command to find out how to use a command. Ex: help <command>\n"
                             "Use the \"commands\" command to list all avaiable commands.")
                return True
            if self.is_controller(controller):
                c = self.find_command_from_controller(controller, args[0])
                if c:
                    handle.print(f"{c['default']}:\n{c['help_info']}")
                    return True
            c = self.find_command(args[0])
            if c:
                handle.print(f"{c['default']}:\n{c['help_info']}")
                return True
            else:
                handle.print(f"Cannot find command {args[0]}")
                return False

        @cls.add_command(["filter", "f"], ignore_chars=ignore, global_function=True,
                         help_info="Modifies filter values.\nThere are multiple modes:"
                                   "\n--on: Turns the filter on."
                                   "\n--off: Turns the filter off."
                                   "\n--reset: Resets the filter entries."
                                   "\n--default <on or off>: Sets the behavior of items that do not have an entry."
                                   "\n--view: Lists filter settings and entries."
                                   "\n--allow <controller> <instance>: Adds an allow entry to the filter."
                                   "\n--disallow <controllers> <instance>: Adds a disallow entry to the filter."
                                   "\nBoth 'allow' and 'disallow' add entries to the filter. The instance argument\n"
                                   "is optional. Without it the entry applies to the entire controller but can be\n"
                                   "overwritten by a specific instance entry.")
        def filter_(self, handle, *args, controller="", instance="", **kwargs):
            if len(args) == 0:
                handle.print("Please supply an argument.")
                return True
            if len(args) > 0 and args[0] == "allow" or args[0] == "disallow":
                cont = controller
                inst = instance
                if len(args) >= 3:
                    cont = args[1]
                    inst = args[2]
                elif len(args) >= 2:
                    cont = args[1]
                handle.modify_filter(args[0] == "allow", controller=cont, instance=inst)
                handle.print("Filter added.")
                return True

            elif "view" in args:
                out = ["----Settings----", f"Enabled: {handle.is_filtered()}"]
                default = handle.get_filter_default()
                if default:
                    out.append("Default: Enabled")
                else:
                    out.append("Default: Disabled")

                f = handle.get_filter()

                t = []
                for i in f["controllers"]:
                    e = "Enabled" if f["controllers"][i] else "Disabled"
                    t.append(f"{i}: {e}")
                if len(t) > 0:
                    out.append("----Controller Filters----")
                    out += t
                t = []
                for i in f["instances"]:
                    e = "Enabled" if f["instances"][i] else "Disabled"
                    t.append(f"{i}: {e}")
                if len(t) > 0:
                    out.append("----Instance Filters----")
                    out += t
                handle.print("\n".join(out))
                return True

            elif "reset" in args:
                handle.reset_filter()
                handle.print("Filter reset.")
                return True

            elif "default" in args:
                if "on" in args:
                    handle.print("Default behavior is on.")
                    handle.set_filter_default(True)
                    return True
                elif "off" in args:
                    handle.print("Default behavior is off.")
                    handle.set_filter_default(False)
                    return True

            elif "on" in args:
                handle.print("Filter enabled.")
                handle.set_filter(True)
                return True
            elif "off" in args:
                handle.print("Filter disabled.")
                handle.set_filter(False)
                return True

        @cls.add_command(["commands"], ignore_chars=ignore, global_function=True,
                         help_info="List all available commands in current scope")
        def commands(self, handle, *args, controller="", instance="", **kwargs):
            result = []
            if self.is_controller(controller):
                c = []
                for command in self.get_commands_from_controller(controller, instance_commands=False):
                    c.append("-"+command["default"])
                if len(c) > 0:
                    result.append(f"----{controller} Controller Commands:----")
                    c.sort()
                    result += c

                c = []
                for command in self.get_commands_from_controller(controller, class_commands=False):
                    c.append("-" + command["default"])
                if len(c) > 0:
                    result.append(f"----{controller} Instance Commands:----")
                    c.sort()
                    result += c

                result.append("----Global Commands:----")
            else:
                result.append("----Main Commands----")
            c = []
            for command in self.parent_object.get_commands():
                c.append("-"+command["default"])
            c.sort()
            result += c
            handle.print("\n".join(result))

        @cls.add_command(["clear"], ignore_chars=ignore, global_function=True,
                         help_info="Clears the console window.")
        def clear(self, handle, *args, **kwargs):
            handle.clear_console()
            return True

        @cls.add_command(["message", "m", "msg"], ignore_chars=ignore, global_function=True,
                         help_info="Send a specified user a message\nEx: message <username> <message>")
        def message(self, handle, *args, **kwargs):
            if len(args) < 1:
                handle.print("Error: No username given.")
                return False
            if len(args) < 2:
                handle.print("Error: No message given.")
                return False
            text = f"[{handle.get_username()}->{args[0]}]:" + " ".join(args[1:])
            res = self.print(args[0], text)
            if res:
                handle.print(text)
                return True
            handle.print(f"Error: Could not find user with name: {args[0]}")
            return False

        @cls.add_command(["shout", "s"], ignore_chars=ignore, global_function=True,
                         help_info="Messages all users with a message")
        def shout(self, handle, *args, **kwargs):
            if len(args) < 1:
                handle.print("Error: No message given.")
                return False
            self.print_all(f"[{handle.get_username()}]:" + " ".join(args))
            return True

        @cls.add_command(["bogos?", "bogos"], ignore_chars=ignore, permission=3, default="bogos",
                         help_info="Bints the bogos")
        def binted(self, handle, *args):
            handle.print("binted")
            return True

        @cls.add_command(["shutdown"], ignore_chars=ignore, permission=5,
                         help_info="Shuts down the Server Server stopping all servers", global_function=True)
        def shutdown(self, handle, *args, **kwargs):
            self.shutdown()
            return True

        @cls.add_command(["focus"], ignore_chars=ignore, global_function=True,
                         help_info="Focuses console onto a specific controller or controller instance. \n"
                                   "Puts all commands into the scope of specified location and limits view"
                                   " of servers to specified location. \n"
                                   "Use unfocus to return. \n"
                                   "Ex: focus <controller> <instance> or /<controller>/<instance>:focus")
        def focus(self, handle, *args, controller="", instance="", **kwargs):
            args = self.join_args(args, [controller, instance])
            if len(args) == 0:
                handle.print("Error: requires at least one argument.")
                return False
            c = args[0]
            ins = ""
            if not self.is_controller(c):
                handle.print(f"Error: cannot find controller with name: {c}")
                return False
            if len(args) > 1:
                ins = args[1]
                if not self.is_server(c, ins):
                    handle.print(f"Error: cannot find instance of {c} with name: {ins}")
                    return False

            handle.set_focus(c, ins)

        @cls.add_command(["unfocus"], ignore_chars=ignore, global_function=True,
                         help_info="Returns focus to global focus")
        def un_focus(self, handle, *args, **kwargs):
            handle.set_focus("", "")

        @cls.add_command(["setpermission", "setperm"], ignore_chars=ignore, global_function=True,
                         help_info="Sets a users permission level."
                                   "\nEx: setpermission <username> <permission>")
        def set_user_permission(self, handle, *args, **kwargs):
            if len(args) < 2:
                handle.print("Error: command requires 2 arguments.")
                return False
            username = args[0]
            permission = args[1]
            if not self.user_data.is_user(username):
                handle.print("Error: user not found.")
                return False
            if not permission.isnumeric() and 0 <= int(permission) <= handle.get_max_permission():
                handle.print(f"Error: permission must be an integer in the range from 0 to "
                             f"{handle.get_max_permission()}.")
                return False
            permission = int(permission)

            if permission >= handle.get_permissions():
                handle.print("Error: can only change permissions to a value lower that yours.")
                return False

            if self.user_data.get_user_data(username, "permission", default=0) \
                    >= handle.get_permissions():
                handle.print("Error: can only change permission of user with lower permission that yours.")
                return False

            self.user_data.set_user_data(username, "permission", permission)
            handle.print(f"Successfully changed {username}'s permission to {permission}.")
            return True
        
        @cls.add_command(["resetpassword", "resetpass"], ignore_chars=ignore, global_function=True, default="reset_password",
                         help_info="Resets a given users password.\nEx: reset_password <username>")
        def reset_password(self, handle, *args, **kwargs):
            if len(args) < 1:
                handle.print("Error: No username specified.")
                return False
            if not self.user_data.is_user(args[0]):
                handle.print(f"Error: Cannot find user with name: {args[0]}")
                return False
            if self.user_data.get_user_data(args[0], "permission", default=0) \
                    >= handle.get_permissions():
                handle.print("Error: can only change reset password of user with lower permission that yours.")
                return False
            self.user_data.set_user_data(args[0], "reset_password", True)
            self.user_data.update_user_password(args[0], password="temp_password")
            handle.print(f"Successfully reset password of {args[0]}")
            return True
        
        @cls.add_command(["getpermissions", "checkpermissions", "checkperms", "perms", "permissions"],
                         ignore_chars=ignore, global_function=True, help_info="Displays the users current permissions")
        def get_permissions(self, handle, *args, **kwargs):
            handle.print(f"Your permission level is {handle.get_permissions()}")
            return True

        @cls.add_command(["createuser", "makeuser", "mkuser"], ignore_chars=ignore, global_function=True,
                         help_info="Creates a user with a given username and optional permission level"
                                   "\nEx: createuser <username> <permission> or createuser <username>")
        def create_user(self, handle, *args, **kwargs):
            if len(args) == 0:
                handle.print("Error: requires at least 1 argument.")
                return False
            username = args[0]
            permissions = 0
            if len(args) > 1:
                if not args[1].isnumeric() or 0 > int(args[1]) > handle.get_max_permission():
                    handle.print(f"Error: permissions value must be an integer between 0 to "
                                 f"{handle.get_max_permission()}.")
                    return False
                permissions = int(args[1])
            if permissions >= handle.get_permissions():
                handle.print("Error: cannot create a user with permissions equal or greater to yourself.")

            if not self.user_data.create_user(username, password="temp_password"):
                handle.print(f"Error: user with name: {username} already exists.")
                return False

            handle.print(f"Successfully created user with name: {username} with permission level: {permissions}.")
            self.user_data.set_user_data(username, "permission", permissions)
            self.user_data.set_user_data(username, "reset_password", True)
            return True

        @cls.add_command(["removeuser", "deleteuser", "rmuser"], ignore_chars=ignore, global_function=True,
                         help_info="Deletes a given user and kicks them off if they are logged in"
                                   "\nEx: removeuser <username>")
        def remove_user(self, handle, *args, **kwargs):
            if len(args) == 0:
                handle.print("Error: requires 1 argument.")
                return False
            username = args[0]
            if not self.user_data.is_users(username):
                handle.print(f"Error: User with {username} does not exist.")
                return False
            if handle.get_permissions() <= \
                    self.user_data.get_user_data(username, "permission", default=0):
                handle.print("Error: Cannot remove user with equal or greater permission level then yourself.")
                return False

            for h in self.handle_list:
                if h.get_username() == username:
                    h.exit()
            self.user_data.remove_user(username)
            handle.print(f"Successfully removed user {username}")
            return True

        @cls.add_command(["users", "listusers"], ignore_chars=ignore, global_function=True,
                         help_info="Lists all users currently online.")
        def list_users(self, handle, *args, **kwargs):
            users_dup = [i.get_username() for i in self.handle_list if i.get_logged_in()]
            users = []
            users = [i for i in users_dup if i not in users]
            users = [f"{i+1}: {v}" for i, v in enumerate(users)]
            if len(users) > 0:
                handle.print(f"{len(users)} total user(s) over {len(users_dup)} connection(s)\n"+"\n".join(users))
            else:
                handle.print("No users online")
            return True

        @cls.add_command(["loadcontrollers", "loadnewcontrollers", "newcontrollers"],
                         ignore_chars=ignore, global_function=True, permission=5,
                         help_info="Checks if new controllers exist and loads them.")
        def load_server_types(self, handle, *args, **kwargs):
            length = len(self.get_server_names())
            self.load_server_types()
            length = len(self.get_server_names()) - length
            handle.print(f"Loaded {length} additional controller(s) from '{self.get_server_types_dir()}'.")

        @cls.add_command(["getcontrollers", "printcontrollers", "listcontrollers", "controllers"],
                         ignore_chars=ignore, global_function=True, permission=1,
                         help_info="Lists of all controllers.")
        def get_server_names(self, handle, *args, **kwargs):
            handle.print("\n".join([str(i[0] + 1) + ": " + i[1] for i in enumerate(self.get_server_names())]))

        @cls.add_command(["reloadcontrollers"], ignore_chars=ignore, global_function=True, permission=5,
                         help_info="Reloads all controllers to update command code.")
        def reload_all_controllers(self, handle, *args, **kwargs):
            for i in self.get_server_names():
                self.console.print("Reloading " + i)
                self.reload_type(i)
            handle.print("Finished Reloading all controllers.")

        @cls.add_command(["reloadcontroller"], ignore_chars=ignore, global_function=True, permission=5,
                         help_info="Reloads a controller from file to update command code."
                                   "\nEx: reloadcontroller <controller>")
        def reload_controller(self, handle, *args, controller="", **kwargs):
            args = self.join_args(args, [controller])
            if len(args) < 1:
                handle.print("Error: Please specify a controller.")
                return False
            if args[0] in self.get_server_names():
                self.reload_type(args[0], handle)
                handle.print("Reloaded " + args[0])
                return True
            handle.print("Error: Not a valid controller.")
            return False

        @cls.add_command(["reloadmanager", "rmanager"], ignore_chars=ignore, global_function=True, permission=5,
                         help_info="Reloads the controller manager from file to update command code.")
        def reload_manager(self, handle, *args, **kwargs):
            self.reload()
            return True

        @cls.add_command(["createserver", "makeserver", "createinstance", "makeinstance", "mkserver", "mkinstance"],
                         ignore_chars=ignore, global_function=True, permission=4,
                         help_info="Creates an instance with a given name of a given controller type"
                                   "\n Ex: createinstance <controller> <name> <additional args>")
        def create_instance(self, handle, *args, controller="", **kwargs):
            args = self.join_args(args, [controller])
            if len(args) > 1:
                if self.create_instance(args[0], args[1], *args[2:]):
                    handle.print(f"Created instance of {args[0]} with name {args[1]}.")
                    return True
            handle.print("Error: invalid arguments.")
            return False

        @cls.add_command(["removeinstance", "deleteinstance", "removeserver", "deleteserver", "rminstance", "rmserver"],
                         ignore_chars=ignore, permission=4,
                         help_info="Deletes an instance if it is not running"
                                   "\nEx: removeinstance <controller> <instance>")
        def remove_instance(self, handle, *args, controller="", instance="", **kwargs):
            args = self.join_args(args, [controller, instance])
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments.")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}.")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}.")
                return False
            if m.get_running():
                handle.print(f"Error: Cannot delete {args[0]}/{args[1]} while it is already running.")
            else:
                if self.remove_instance(args[0], args[1]):
                    handle.print(f"Removed instance of {args[0]} with name {args[1]}")
                    return True
            handle.print("Error: invalid arguments.")

        @cls.add_command(["saveinstances", 'saveservers'], ignore_chars=ignore, global_function=True, permission=2,
                         help_info="Saves instance config to file, done automatically on shutdown.")
        def save(self, handle, *args, **kwargs):
            if self.save_instances_to_file():
                handle.print("Saved instances to file.")
                return True
            handle.print("Failed to save instances to file.")
            return False

        @cls.add_command(["listinstances", "printinstances", "instances", "servers"],
                         ignore_chars=ignore, global_function=True, permission=1, help_info="Lists all instances")
        def list_instances(self, handle, *args, controller="", **kwargs):
            out = []

            for i in self.get_server_names():
                if controller and controller != i:
                    continue
                instances = self.get_names_of_server_from_type(i)
                for name in instances:
                    out.append(f"{i}: {name}")
            if len(out) == 0:
                handle.print("No instances to list.")
                return False
            out = [f"{i + 1}: {v}" for i, v in enumerate(out)]
            handle.print("\n".join(out))
            return True

        @cls.add_command(["instanceinfo", "serverinfo"], ignore_chars=ignore, global_function=True, permission=1,
                         help_info="Lists info of a given server.\nEx: instanceinfo <controller> <instance>")
        def instance_info(self, handle, *args, controller="", instance="", **kwargs):
            args = self.join_args(args, [controller, instance])
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments.")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}.")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}.")
                return False
            output = f"Name: {args[1]}"\
                     f"\nController: {args[0]}"\
                     f"\nRunning: {m.get_running()}"\
                     f"\nAddress: {m.get_address()}"
            instance_info = m.get_info()
            if instance_info:
                output += f"\n{instance_info}"
            handle.print(output)

        @cls.add_command(["start"], ignore_chars=ignore, global_function=True, permission=3,
                         help_info="Starts an instance.\nEx: start <controller> <instance>")
        def start_instance(self, handle, *args, controller="", instance="", **kwargs):
            args = self.join_args(args, [controller, instance])
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments.")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}.")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}.")
                return False

            if m.get_running():
                handle.print(f"Error: {args[0]}/{args[1]} is already running.")
            else:
                m.start()
                handle.print(f"Starting {args[0]}/{args[1]}.")

        @cls.add_command(["setup"], ignore_chars=ignore, global_function=True, permission=3,
                         help_info="Runs the setup of an instance without running it if possible."
                                   "\nEx: setup <controller> <instance>")
        def setup_instance(self, handle, *args, controller="", instance="", **kwargs):
            args = self.join_args(args, [controller, instance])
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments.")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}.")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}.")
                return False

            if m.get_running():
                handle.print(f"Error: {args[0]}/{args[1]} is running.")
                return False
            m.setup()
            handle.print(f"Setting up {args[0]}/{args[1]}.")
            return True

        @cls.add_command(["stop"], ignore_chars=ignore, global_function=True, permission=3,
                         help_info="Stops an instance.\nEx: stop <controller> <instance>")
        def stop_instance(self, handle, *args, controller="", instance="", **kwargs):
            args = self.join_args(args, [controller, instance])
            if len(args) < 2:
                handle.print("Error: Requires 2 arguments.")
                return False
            if args[0] not in self.get_server_names():
                handle.print(f"Error: Cannot find controller with name: {args[0]}.")
                return False
            m = self.get_instance_from_type_and_name(args[0], args[1])
            if not m:
                handle.print(f"Error: Cannot find instance with name: {args[1]}.")
                return False

            if not m.get_running():
                handle.print(f"Error: {args[0]}/{args[1]} is not running.")
                return False
            m.stop()
            handle.print(f"Stopping {args[0]}/{args[1]}.")
            return True

    # </editor-fold>

    def __init__(self, ConsoleObj, handle_list, port_handler, env_path, socket_server, user_data, gui, config):
        self.parent_object = type(self)
        self.objects.append(self)

        self.console = ConsoleObj  # FOR DEBUG, remove later
        self.port_handler = port_handler
        self.server_types_dir = ""
        self.server_types = {}  # format {type: {"module": module, "file": filename}}

        self.instances_data_file = ""
        self.server_dir = ""
        self.instances = {}     # format {type: [instance1, instance2, ...]}

        self.env_manager = EnvManager(env_path)
        self.socket_server = socket_server
        self.user_data = user_data
        self.gui = gui

        self.config = config
        self.handle_list = handle_list

        self.reload_needed = False
        self.shutdown_needed = False

    def get_handle_list(self):
        return self.handle_list

    def get_config(self):
        return self.config

    def get_user_data(self):
        return self.user_data

    def get_gui(self):
        return self.gui

    def get_env_manager(self):
        return self.env_manager

    def reload(self):
        self.reload_needed = True

    def shutdown(self):
        self.shutdown_needed = True

    def get_reload_needed(self):
        return self.reload_needed

    def get_shutdown_needed(self):
        return self.shutdown_needed

    def remove(self):
        self.parent_object.remove(self)
        return True

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object
        self.reload_needed = False
        return True

    def run_command(self, name, handle, *args, **kwargs):
        path_given = "module_name" in kwargs or "controller" in kwargs
        for i in self.parent_object.commands:
            temp_name = remove_chars(name, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                if handle.get_permissions() < i["permission"]:
                    handle.print("You don't have permission to run that command")
                    return True
                if path_given:
                    if not i["global"]:
                        continue
                try:
                    i["function"](self, handle, *args, **kwargs)
                    return True
                except Exception as e:
                    handle.print(f"Error running {name}, Error: {e.__repr__()}")
                    return True
        return False

    def run_command_on_server_type(self, server_type, name, user, *args, **kwargs):
        if server_type not in self.server_types:
            return False
        return self.server_types[server_type]["module"].run_class_command(name, user, *args, **kwargs)

    def run_command_on_server_instance(self, server_type, controller_name, name, user, *args, **kwargs):
        instance = self.get_instance_from_type_and_name(server_type, controller_name)
        if instance:
            return instance.run_command(name, user, *args, **kwargs)
        return False

    def find_command_from_controller(self, controller, command, class_commands=True, instance_commands=True):
        if controller not in self.server_types:
            return False
        return self.server_types[controller]["module"].find_command(command, class_commands=class_commands,
                                                                    instance_commands=instance_commands)

    def get_commands_from_controller(self, controller, class_commands=True, instance_commands=True):
        if controller not in self.server_types:
            return False
        return self.server_types[controller]["module"].get_commands(class_commands=class_commands,
                                                                    instance_commands=instance_commands)

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

    def is_controller(self, controller):
        return controller in self.server_types

    def is_server(self, controller, server):
        if not self.is_controller(controller):
            return False
        return server in self.get_names_of_server_from_type(controller)

    def get_names_of_server_from_type(self, type_):
        if type_ not in self.instances:
            return []
        return [i.get_name() for i in self.instances[type_]]

    def get_instance_from_type_and_name(self, type_, name):
        if type_ not in self.instances:
            return
        list_ = self.instances[type_]
        for i in list_:
            if i.get_name() == name:
                return i

    def load_server_types(self):
        if not self.server_types_dir:
            return False
        files = listdir(self.server_types_dir)
        loaded_files = [self.server_types[i]["file"] for i in self.server_types]
        for file in files:
            if file.endswith(".py"):
                if file not in loaded_files:
                    try:
                        module = module_from_file(ospath.join(self.server_types_dir, file), "Controller")
                        module.set_manager(self)
                        module.init_class()
                        self.server_types[module.type] = {"module": module, "file": file}
                    except AttributeError:
                        pass
        self.init_instance_storage()
        return True

    def reload_type(self, name, c=None):
        if name in self.server_types:
            ty = self.server_types[name]
            file = ty["file"]
            module = ty["module"]

            obj = module.get_objects()

            try:
                new_mod = module_from_file(ospath.join(self.server_types_dir, file), "Controller")
                new_mod.reset_commands()
                new_mod.set_manager(self)
                new_mod.set_objects(obj)
                new_mod.init_class()
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
        m = self.server_types[type_]["module"](name, data, self.port_handler(), *args)
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
                if not instance.get_running():
                    instance.remove()
                    del self.instances[type_][index]
                    return True
        return False

    def load_instances_from_file(self):
        file = open(self.instances_data_file, "r")
        try:
            data = loads(file.read())
        except IOError:
            return False
        except decoder.JSONDecodeError:
            return False
        file.close()

        self.init_instance_storage()

        for i in data:
            list_ = data[i]
            for instance in list_:
                ins = self._create_instance_r(i, instance["name"], instance["data"])
                if ins:
                    self.instances[i].append(ins)
        return True

    def save_instances_to_file(self):
        data = {}

        for i in self.get_server_names():
            data[i] = []

        for i in self.instances:
            list_ = self.instances[i]
            for instance in list_:
                data[i].append({"name": instance.get_name(), "data": instance.get_data()})

        file = open(self.instances_data_file, "w")
        file.write(dumps(data))
        file.close()
        return True

    def print_all(self, value, focus=None):
        usernames = []
        for user in self.handle_list:
            name = user.get_username()
            if name not in usernames:
                usernames.append(name)
                self.print(name, value, focus=focus)

    def print(self, username, value, focus=None):
        found = False
        for user in self.handle_list:
            if user.get_logged_in() and user.get_username() == username:
                if not focus:
                    user.print(value)
                elif user.is_focused():
                    if user.check_focus(focus):
                        user.print(value)
                elif user.is_filtered():
                    if user.check_filter(focus):
                        user.print(value)
                else:
                    user.print(value)
                found = True
        return found

    def flush_servers(self):
        for types in self.instances:
            for instances in self.instances[types]:
                items = instances.get_queue()
                for item in items:
                    self.print_all(item, focus=(types, instances.get_name()))

    def close_instances(self):
        for cont in self.instances:
            for ins in self.instances[cont]:
                ins.stop()
                ins.shutdown()

        running = True
        while running:
            sleep(0.1)
            running = False
            for cont in self.instances:
                for ins in self.instances[cont]:
                    running = running or ins.get_running()

    def get_status(self):
        status = []
        status.append(version)
        status.append(f"Loaded {len(self.user_data.get_users())} user(s) from '{self.user_data.get_file_path()}'")
        status.append(f"Loaded {len(self.get_server_names())} server type(s) from '{self.instances_data_file}'")
        if self.gui.get_running():
            status.append(f"Hosted web server at {self.port_handler.get_connection_to_port(self.gui.get_port())}")
        else:
            status.append(f"Web server: Disconnected")
        if self.socket_server.get_running():
            status.append(
                f"Hosted socket server at {self.port_handler.get_connection_to_port(self.socket_server.get_port())}")
        else:
            status.append(f"Socket server: Disconnected")
        status.append(f"UPNP: " + ("Working" if self.port_handler.upnp.get_connected() else "Disconnected"))
        status.append(f"CloudFlare: " + ("Working" if self.port_handler.cloudflare.get_connected() else "Disconnected"))
        return status
