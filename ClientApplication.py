from Classes import Client
from Classes import ConsoleUI
import time

ip = "127.0.0.1"
port = 10000


console = ConsoleUI()
console.start()
console.update_prefix("->")

C = Client()
C.set_ip(ip)
C.set_port(port)


console.print(f"Connection to {ip}:{port}")
C.start()


running = True
while running:
    time.sleep(0.1)
    if not C.get_running():
        running = False
        break
    inp = console.get_input()
    for i in inp:
        if i.lower() == "exit":
            running = False
        else:
            C.send_packet({"type": "text", "text": i})
    for p in C.get_all_packets():
        if p["type"] == "text":
            console.print(p["text"], p["newline"], p["loop"])
C.stop()
console.stop()

