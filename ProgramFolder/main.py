from Classes import ConsoleUI
from Classes import UserData
from Classes import Server
from Classes import ControllerManager
from Classes import UserHandle
from Classes import functions
from Classes import PortHandler
from Classes import GUI
from json import dumps, loads, JSONDecodeError
from time import sleep, time
from sys import version
from socket import gethostbyname, gethostname
from os import path as ospath, chdir, getcwd, system, getpid, kill, remove
from sys import argv, executable
from platform import system as platSys

# STUFF TO DO
# prevent subdomain overlap
# upnp prevent overlap with normal port forwarded ports
# organize client application (its very messy and bad right now)
# make change password server side command
# help for controllers
# webserver option in config
# secure the webserver

# LIKE TO DO
# something with logging
# add more servers (factorio)
# run as admin
# discord bot controller
# hard exit servers in the event they hang/crash
# commands/documentation
# typing
# execute commands from in game
# permission to view server output

# ---minecraft controller stuff
# edit Settings
# whitelisting stuff
# manage bans
# output parsing
# change version
# backup/change worlds


def main(config):
    if not isinstance(config["ip"], str) or len(config["ip"].split(".")) != 4:
        config["ip"] = gethostbyname(gethostname())
    PortHandler.get_public_ip()
    PortHandler.set_ip(config["ip"])
    PortHandler.set_use_upnp(config["upnp"])
    PortHandler.initialize_upnp()
    PortHandler.set_use_cloudflare(config["cloudflare"])
    PortHandler.initialize_cloudflare(config["cloudflareEmail"], config["cloudflareApiKey"],
                                      config["cloudflareDomain"], "serverserver")
    PortHandler.wipe_ports()

    user_handles = []

    Console = ConsoleUI()
    UserInfo = UserData()
    MainServer = Server()
    Manager = ControllerManager.ControllerManager(Console, user_handles, PortHandler, config['envDir'], MainServer)
    Gui = GUI(Manager)

    if not config["headless"]:
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
    MainServer.set_port(server_port_handler.request_port(config['socketPort'], description="Controller", TCP=True))
    MainServer.start()

    Gui.set_ip(config["ip"])
    Gui.set_port(server_port_handler.request_port(config['webServerPort'], description="WebServer"))
    Gui.start()
    Console.print(f"Hosted web server at {PortHandler.get_connection_to_port(Gui.get_port())}")
    Console.print(f"Hosted socket server at {PortHandler.get_connection_to_port(MainServer.get_port())}")
    Console.print(f"UPNP: " + ("Working" if PortHandler.upnp.get_connected() else "Disconnected"))
    Console.print(f"CloudFlare: " + ("Working" if PortHandler.cloudflare.get_connected() else "Disconnected"))

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
                        if command.startswith("/"):
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
    Gui.stop()
    server_port_handler.remove()

    start_time = time()

    while MainServer.running:
        sleep(0.25)
        if start_time + 30 < time():
            break

    Console.print("Goodbye")
    sleep(0.5)
    Console.stop()
    exit()


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        kill(int(pid), 0)
    except OSError:
        return False
    except ValueError:
        return False
    except SystemError:
        return False
    else:
        return True


if __name__ == "__main__":

    chdir(ospath.dirname(ospath.join(argv[0], __file__)))

    # <editor-fold desc="Base Config Values">
    configFilePath = "data/config.json"

    default_config = {
        "userInfoFile": "data/userdata.json",
        "serverInfoDir": "serverTypes/",
        "instanceDataFile": "data/controllerInstances.json",
        "serverDir": "../ServerFolder",
        "pidFile": "data/serverserver.pid",
        "envDir": "Env",
        "socketPort": 10000,
        "webServerPort": 80,
        "ip": "127.0.0.1",
        "headless": False,
        "upnp": False,
        "cloudflare": False,
        "cloudflareEmail": "",
        "cloudflareApiKey": "",
        "cloudflareDomain": ""
    }

    # </editor-fold>

    # <editor-fold desc="Config File Loading">
    try:
        f = open(configFilePath, "r")
        data = f.read()
        f.close()
    except IOError:
        data = ""
        write_data = dumps(default_config)
        try:
            f = open(configFilePath, "w")
            f.write(write_data)
            f.close()
        except IOError:
            pass
    try:
        configData = loads(data)
    except JSONDecodeError:
        configData = {}

    for config_key in default_config:
        configData[config_key] = configData.get(config_key, default_config[config_key])
    # </editor-fold>

    no_new = len(argv) > 1 and "headless" in argv[1:]
    script = ospath.join(getcwd(), ospath.basename(__file__))
    if configData["headless"] and not no_new:
        if platSys() == "Windows":
            system(f"start {executable[:-4]}w.exe {script} headless")
        elif platSys() == "Linux":
            system(f"nohup {executable} {script} headless &")
        elif platSys() == "Darwin":
            system(f"{executable} {script} headless &")

    else:
        try:
            if ospath.isfile(configData["pidFile"]):
                with open(configData["pidFile"], "r") as f:
                    if check_pid(f.read()):
                        exit()
            with open(configData["pidFile"], "w") as f:
                f.write(str(getpid()))
            main(configData)
        except Exception as e:
            c = ConsoleUI()
            c.start()
            c.stop()
            raise e
        finally:
            if ospath.isfile(configData["pidFile"]):
                remove(configData["pidFile"])
