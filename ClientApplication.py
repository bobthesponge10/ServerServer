from ProgramFolder.Classes import Client
from ProgramFolder.Classes import ConsoleUI
from ProgramFolder.Classes import UserData
import time

ip = "127.0.0.1"
port = 10000


console = ConsoleUI()
console.start()


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
while not logged_in:
    time.sleep(0.1)
    if not C.get_running():
        break

    for i in console.get_input():
        if login_state == 0:
            username = i
            console.update_prefix("Password: ")
            console.clear_input_history()
            login_state = 1
        elif login_state == 1:
            password = i
            C.send_packet({"type": "login_username", "username": username})
            console.update_prefix("Waiting. . .")
            console.clear_input_history()
            login_state = 2
    for packet in C.get_all_packets():
        if packet["type"] == "login_alg_and_salt":
            hash_ = UserData.generate_hash(packet.get("salt") + password, packet.get("alg"))
            C.send_packet({"type": "final_login", "username": username, "hash": hash_})
        elif packet["type"] == "login_response":
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
console.update_prefix("->")
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

