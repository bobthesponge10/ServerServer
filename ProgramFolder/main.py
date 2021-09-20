from Classes import ConsoleUI
from Classes import UserData
from Classes import Server
from Classes import functions
from Classes import ControllerManager
from Classes import UserHandle
from Classes import functions
import time
import os
import sys


# add server.properties write each time before server boot in case info changed

def main():

    # <editor-fold desc="File Paths">
    userInfoFile = "ProgramFolder/data/userdata.json"
    serverInfoDir = "ProgramFolder/serverTypes/"
    instanceDataFile = "ProgramFolder/data/controllerInstances.json"
    serverDir = "ServerFolder"
    # </editor-fold>

    os.chdir(os.path.dirname(os.path.dirname(__file__)))

    user_handles = []

    Console = ConsoleUI()
    UserInfo = UserData()
    MainServer = Server()
    Manager = ControllerManager(Console, user_handles)

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

    running = True

    ServerHandle = UserHandle(Console, server=True)

    user_handles.append(ServerHandle)

    while running:
        time.sleep(0.1)

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
                elif len(i_) > 0:
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
                                Manager.run_command_on_server_instance(module_name, controller, actual_command,
                                                                                                        user, *args)
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

    Console.stop()


if __name__ == "__main__":
    main()
