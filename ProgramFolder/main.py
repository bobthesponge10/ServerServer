from Classes import ConsoleUI
from Classes import UserData
from Classes import Server
from Classes import ControllerManager
from Classes import UserHandle
from Classes import functions
from Classes import PortHandler
import time
import os
import sys

# STUFF TO DO
# commands/documentation
# type scripting
# user login
# user chat functionality
# permissions
# user filter view
# user focus on specific server
# something with logging
# help commands
# using global commands in focus
# add more servers (factorio)
# upnp support
# cloudflare api integration
# run as admin
# auto download java env
# discord bot controller
# config file, things like autorun commands, file paths, etc

# ---minecraft controller stuff
# edit Settings
# whitelist stuff
# output parsing
# error handling
# change version
# backup/change worlds


def main():

    # <editor-fold desc="File Paths">
    userInfoFile = "ProgramFolder/data/userdata.json"
    serverInfoDir = "ProgramFolder/serverTypes/"
    instanceDataFile = "ProgramFolder/data/controllerInstances.json"
    serverDir = "ServerFolder"
    envDir = "ProgramFolder/Env"
    # </editor-fold>

    os.chdir(os.path.dirname(os.path.dirname(__file__)))

    user_handles = []

    Console = ConsoleUI()
    UserInfo = UserData()
    MainServer = Server()
    Manager = ControllerManager(Console, user_handles, PortHandler)

    Console.start()
    Console.update_prefix("->")

    UserInfo.set_file_path(userInfoFile)
    UserInfo.load()

    Manager.set_server_types_dir(serverInfoDir)
    Manager.set_instance_data_file(instanceDataFile)
    Manager.set_server_dir(serverDir)
    Manager.init_commands()
    Manager.load_server_types()
    Manager.load_instances_from_file()

    Console.print(sys.version)
    Console.print(f"Loaded {len(UserInfo.get_users())} user(s) from '{userInfoFile}'")
    Console.print(f"Loaded {len(Manager.get_server_names())} server type(s) from '{serverInfoDir}'")

    server_port_handler = PortHandler()
    MainServer.set_port(server_port_handler.request_port(10000))
    MainServer.start()
    Console.print(f"Hosted socket server at {MainServer.get_ip()}:{MainServer.get_port()}")

    ServerHandle = UserHandle(Console, server=True)
    user_handles.append(ServerHandle)

    running = True
    while running:
        time.sleep(0.01)

        for i in MainServer.get_new_connections():
            connection = MainServer.get_client_from_id(i)
            user_handle = UserHandle(connection, id_=i)
            user_handles.append(user_handle)
            Manager.print_all(f"Got connection from {connection.get_addr()}")

        for i in MainServer.get_old_connections():
            for h in user_handles:
                if h.get_id() == i:
                    user_handles.remove(h)
                    Manager.print_all(f"Lost connection from {h.get_obj().get_addr()}")
                    break

        Manager.flush_servers()

        if Manager.get_reload_needed():
            file = ControllerManager.get_file()
            o = ControllerManager.get_objects()

            ControllerManager_ = functions.module_from_file(file, "ControllerManager")
            ControllerManager_.set_objects(o)
            ControllerManager_.init_commands()
            ControllerManager_.set_file(file)
            Manager.print_all("Reloaded controller manager")

        for user in user_handles:
            items = user.get_input()
            for i_ in items:
                if i_.lower() == "exit":
                    running = False
                elif i_.lower() == "clear":
                    if user.is_server():
                        Console.clear_console()
                elif len(i_) > 0:
                    if user.is_server():
                        user.print(">" + i_)

                    parsed = functions.parse_string_for_commands(i_)
                    if len(parsed) > 0:
                        command = parsed[0]
                        args = parsed[1:]

                        if command.startswith("/"):
                            spl1 = command[1:].split(":")
                            path = spl1[0]
                            actual_command = ":".join(spl1[1:])
                            path = [i for i in path.split("/") if len(i) > 0]

                            if len(path) == 1:
                                module_name = path[0]
                                Manager.run_command_on_server_type(module_name, actual_command, user, *args)

                            elif len(path) == 2:
                                module_name = path[0]
                                controller = path[1]
                                Manager.run_command_on_server_instance(
                                    module_name, controller, actual_command, user, *args)
                        else:
                            Manager.run_command(command, user, *args)

    Console.print("Closing Server Instances")
    Manager.close_instances()
    Console.print("Saving user data")
    UserInfo.save()
    Console.print("Saving module data")
    Manager.save_instances_to_file()
    Console.print("Stopping socket server")
    MainServer.stop()

    while MainServer.running:
        time.sleep(0.25)

    Console.print("Goodbye")
    time.sleep(0.5)
    Console.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        c = ConsoleUI()
        c.start()
        c.stop()
        raise e
