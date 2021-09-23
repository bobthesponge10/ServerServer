from threading import Thread
import time


class UserHandle:
    def __init__(self, obj, user_data, server=False, id_=-1, manager=None):
        self.obj = obj
        self.manager = manager
        self.server = server
        self.id = id_
        self.user_data = user_data
        self.packets = []

        self.logged_in = False
        self.login_thread = None
        self.username = ""

        self.max_permission = 5

        self.running = True

        if not self.server:
            self.login()

    def login(self):
        self.login_thread = Thread(target=self.login_process, daemon=True)
        self.login_thread.start()

    def login_process(self):
        while self.running:
            try:
                time.sleep(0.1)
                p = self.get_packets(["login_username", "final_login"])
                for packet in p:
                    if packet["type"] == "login_username":
                        username = packet.get("username")
                        if username in self.user_data.get_users():
                            alg, salt = self.user_data.get_hash_and_salt(username)
                            self.obj.send_packet({"type": "login_alg_and_salt", "alg": alg, "salt": salt})
                        else:
                            self.obj.send_packet({"type": "login_alg_and_salt", "alg": self.user_data.get_latest_hash(),
                                                  "salt": self.user_data.generate_random_string()})
                    elif packet["type"] == "final_login":
                        username = packet.get("username")
                        hash_ = packet.get("hash")
                        if self.user_data.login_user(username, password_hash=hash_):
                            self.running = False
                            self.logged_in = True
                            self.username = username
                            self.obj.send_packet({"type": "login_response", "response": "success"})
                            self.manager.print_all(f"Got connection from {self.username}")

                        else:
                            self.obj.send_packet({"type": "login_response", "response": "failure"})
            except Exception as e:
                self.print(str(e))

    def print(self, data, newline=True, loop=True):
        if self.server:
            self.obj.print(data, newline=newline, loop=loop)
        else:
            self.obj.send_packet({"type": "text", "newline": newline, "loop": loop, "text": f"{data}"})

    def get_input(self):
        if self.server:
            return self.obj.get_input()
        return [i.get("text") for i in self.get_packets("text")]

    def get_username(self):
        return self.username

    def get_packets(self, type_):
        if not isinstance(type_, list):
            type_ = [type_]
        self.packets += self.obj.get_all_packets()
        out = []
        p = []
        for i in self.packets:
            if i["type"] in type_:
                out.append(i)
            else:
                p.append(i)
        self.packets = p
        return out

    def wait_for_packets(self, type_, timeout=-1):
        start_time = time.time()
        while True:
            packets = self.get_packets(type_)
            if len(packets) > 0:
                return packets
            if timeout != -1 and start_time + timeout < time.time():
                return []

    def is_server(self):
        return self.server

    def get_permissions(self):
        if self.server:
            return self.max_permission
        elif self.logged_in:
            return self.user_data.get_user_data(self.username, "permission", default=0)
        else:
            return 0

    def get_user_data_obj(self):
        return self.user_data

    def get_max_permission(self):
        return self.max_permission

    def get_logged_in(self):
        return self.logged_in or self.server

    def get_obj(self):
        return self.obj

    def get_id(self):
        return self.id

    def exit(self):
        self.running = False
