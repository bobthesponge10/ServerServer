from ProgramFolder.Classes import Client
from ProgramFolder.Classes import ConsoleUI
from ProgramFolder.Classes import UserData
import time
import json


def change_password(console_, client_, algorithm):
    salt = UserData.generate_random_string()
    alg = algorithm
    console_.set_obscure(True)
    console_.update_prefix("Set new password: ")
    running = True
    while running:
        inp = console_.get_input()
        for i in inp:
            if len(i) > 0:
                console_.set_obscure(False)
                password = i
                hash_ = UserData.generate_hash(salt + password, alg)
                client_.send_packet({"type": "change_password", "salt": salt, "hash": hash_, "alg": alg})
                running = False
    console_.set_obscure(False)
    console_.update_prefix("->")
    console_.clear_input_history()


config_file = "config.json"
starting_prefix = "->"

# <editor-fold desc="Loads config data from file">

ip = ""
port = -1

try:
    file = open(config_file, "r")
    data = file.read()
    file.close()
except IOError:
    data = ""
try:
    config = json.loads(data)
except json.JSONDecodeError:
    config = {}

ip = config.get("ip", ip)
port = config.get("port", port)

# </editor-fold>

valid_address = True
if port <= 0 or port > 65535:
    valid_address = False
elif len(ip.split(".")) != 4:
    valid_address = False

console = ConsoleUI()
console.start()

if not valid_address:
    console.update_prefix("Address: ")
    address = console.wait_get_input()+":"
    ip = address.split(":")[0]
    try:
        port = int(address.split(":")[1])
    except ValueError:
        port = 10000
    console.update_prefix(starting_prefix)

C = Client()
C.set_ip(ip)
C.set_port(port)
C.wait_time = 0.01

console.print(f"Connecting to {ip}:{port}")
C.start()

console.update_prefix("Username: ")
login_state = 0
logged_in = False
username = ""
password = ""
salt = ""
alg = ""
reset_password = False
while not logged_in:
    time.sleep(0.1)
    if not C.get_running():
        break

    for i in console.get_input():
        if login_state == 0:
            username = i
            console.update_prefix("Waiting. . .")
            console.clear_input_history()
            C.send_packet({"type": "login_username", "username": username})
            login_state = 1
        elif login_state == 2:
            password = i
            console.set_obscure(False)
            console.update_prefix("Waiting. . .")
            console.clear_input_history()
            hash_ = UserData.generate_hash(salt + password, alg)
            C.send_packet({"type": "final_login", "username": username, "hash": hash_})
            login_state = 3
    for packet in C.get_all_packets():
        if packet["type"] == "login_alg_and_salt" and login_state == 1:
            salt = packet.get("salt")
            alg = packet.get("alg")
            reset_password = packet.get("reset_password")
            console.set_obscure(True)
            if not reset_password:
                console.update_prefix("Password: ")
            else:
                console.update_prefix("Set new password: ")
            login_state = 2
        elif packet["type"] == "login_response" and login_state == 3:
            if packet.get("response") == "success":
                logged_in = True
                break
            else:
                login_state = 0
                console.print("Invalid username or password")
                console.update_prefix("Username: ")

console.clear_input_history()
console.clear_console()
password = ""
console.print(f"Successfully logged in as: {username}")
console.update_prefix(starting_prefix)
running = C.get_running()
while running:
    time.sleep(0.1)
    if not C.get_running():
        running = False
        break
    for i in console.get_input():
        if i.lower() == "exit":
            running = False
        elif i.lower() == "clear":
            console.clear_console()
        elif i.lower() == "changepass":
            change_password(console, C, alg)
        else:
            console.print(">" + i)
            C.send_packet({"type": "text", "text": i})
    for p in C.get_all_packets():
        if p["type"] == "text":
            console.print(p["text"], p["newline"], p["loop"])
        elif p["type"] == "set_prefix":
            console.update_prefix(p.get("text"))
C.stop()
console.stop()

