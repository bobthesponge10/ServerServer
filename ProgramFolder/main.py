from Classes import ConsoleUI
from Classes import UserData
from Classes import Server
from Classes import ControllerManager
from Classes import UserHandle
from Classes import functions
from Classes import PortHandler
from json import dumps, loads, JSONDecodeError
from time import sleep
from os import chdir
from os import path as ospath
from sys import version
from socket import gethostbyname, gethostname

# STUFF TO DO

# LIKE TO DO
# something with logging
# add more servers (factorio)
# upnp support
# cloudflare api integration
# run as admin
# discord bot controller
# hard exit servers in the event they hang/crash
# commands/documentation
# typing
# execute commands from in game
# permission tp view server output
# obscure text when typing password
# headless mode
# organize client application (its very messy and bad right now)

# ---minecraft controller stuff
# edit Settings
# whitelist stuff
# manage bans
# output parsing
# error handling
# change version
# backup/change worlds


def main():

    # <editor-fold desc="Base Config Values">
    configFilePath = "ProgramFolder/data/config.json"

    default_config = {
        "userInfoFile": "ProgramFolder/data/userdata.json",
        "serverInfoDir": "ProgramFolder/serverTypes/",
        "instanceDataFile": "ProgramFolder/data/controllerInstances.json",
        "serverDir": "ServerFolder",
        "envDir": "ProgramFolder/Env",
        "socketPort": 10000,
        "ip": "127.0.0.1"
    }

    # </editor-fold>

    # <editor-fold desc="Config File Loading">
    try:
        file = open(configFilePath, "r")
        data = file.read()
        file.close()
    except IOError:
        data = ""
        write_data = dumps(default_config)
        try:
            file = open(configFilePath, "w")
            file.write(write_data)
            file.close()
        except IOError:
            pass
    try:
        config = loads(data)
    except JSONDecodeError:
        config = {}

    for i in default_config:
        config[i] = config.get(i, default_config[i])
    # </editor-fold>

    if not isinstance(config["ip"], str) or len(config["ip"].split(".")) != 4:
        config["ip"] = gethostbyname(gethostname())
    PortHandler.set_ip(config["ip"])

    chdir(ospath.dirname(ospath.dirname(__file__)))

    user_handles = []

    Console = ConsoleUI()
    UserInfo = UserData()
    MainServer = Server()
    Manager = ControllerManager.ControllerManager(Console, user_handles, PortHandler, config['envDir'])

    Console.start()
    Console.update_prefix("->")

    UserInfo.set_file_path(config["userInfoFile"])
    UserInfo.load()

    Manager.set_server_types_dir(config["serverInfoDir"])
    Manager.set_instance_data_file(config["instanceDataFile"])
    Manager.set_server_dir(config["serverDir"])
    Manager.init_commands()
    Manager.load_server_types()
    Manager.load_instances_from_file()

    Console.print(version)
    Console.print(f"Loaded {len(UserInfo.get_users())} user(s) from '{config['userInfoFile']}'")
    Console.print(f"Loaded {len(Manager.get_server_names())} server type(s) from '{config['serverInfoDir']}'")

    server_port_handler = PortHandler()
    MainServer.set_ip(config["ip"])
    MainServer.set_port(server_port_handler.request_port(config['socketPort']))
    MainServer.start()
    Console.print(f"Hosted socket server at {MainServer.get_ip()}:{MainServer.get_port()}")

    ServerHandle = UserHandle(Console, UserInfo, server=True)
    user_handles.append(ServerHandle)

    running = True
    while running:
        sleep(0.01)

        for i in MainServer.get_new_connections():
            connection = MainServer.get_client_from_id(i)
            user_handle = UserHandle(connection, UserInfo, id_=i, manager=Manager)
            user_handles.append(user_handle)

        for i in MainServer.get_old_connections():
            for h in user_handles:
                if h.get_id() == i:
                    h.exit()
                    user_handles.remove(h)
                    name = h.get_username()
                    if name:
                        Manager.print_all(f"Lost connection from {name}")
                    break

        if Manager.get_reload_needed():
            file = ControllerManager.ControllerManager.get_file()
            o = ControllerManager.ControllerManager.get_objects()

            ControllerManager_ = functions.reload_module(ControllerManager).ControllerManager
            ControllerManager_.set_objects(o)
            ControllerManager_.init_commands()
            ControllerManager_.set_file(file)
            Manager.print_all("Reloaded controller manager")

        if Manager.get_shutdown_needed():
            Manager.print_all("Server Shutting down")
            running = False

        Manager.flush_servers()

        for user in user_handles:
            user.update()
            items = user.get_input()
            for i_ in items:
                if len(i_) > 0:
                    if user.is_server():
                        user.print(">" + i_)

                    parsed = functions.parse_string_for_commands(i_)
                    if len(parsed) > 0:
                        command = parsed[0]
                        args = parsed[1:]
                        result = False
                        if user.is_server() and command.lower() == "clear":
                            Console.clear_console()
                            result = True
                        elif command.startswith("/"):
                            spl1 = command[1:].split(":")
                            path = spl1[0]
                            actual_command = ":".join(spl1[1:])
                            path = [i for i in path.split("/") if len(i) > 0]

                            if len(path) == 1:
                                controller = path[0]
                                result = Manager.run_command_on_server_type(controller, actual_command, user, *args)
                                if not result:
                                    result = Manager.run_command(actual_command, user, *args,
                                                                 controller=controller)

                            elif len(path) == 2:
                                controller = path[0]
                                instance = path[1]
                                result = Manager.run_command_on_server_instance(
                                    controller, instance, actual_command, user, *args)
                                if not result:
                                    result = Manager.run_command(actual_command, user, *args,
                                                                 controller=controller, instance=instance)

                        else:
                            result = Manager.run_command(command, user, *args)

                        if not result:
                            user.print("Error: unknown command. Try the \"help\" command")

    for handle in user_handles:
        handle.exit()

    Console.print("Closing Server Instances")
    Manager.close_instances()
    Console.print("Saving user data")
    UserInfo.save()
    Console.print("Saving module data")
    Manager.save_instances_to_file()
    Console.print("Stopping socket server")
    MainServer.stop()

    while MainServer.running:
        sleep(0.25)

    Console.print("Goodbye")
    sleep(0.5)
    Console.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        c = ConsoleUI()
        c.start()
        c.stop()
        raise e
