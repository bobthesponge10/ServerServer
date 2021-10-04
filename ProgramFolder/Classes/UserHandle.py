from threading import Thread
from time import time, sleep


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

        self.focus = ("", "")
        self.default_prefix = "->"
        self.serverName = "SERVER"
        self.max_permission = 5

        self.filter_enabled = False
        self.default_filter_behavior = True  # True = allow if not specified; False = disallow if not specified
        self.filters = {}
        self.reset_filter()

        self.running = True

        if not self.server:
            self.login()

    def login(self):
        self.login_thread = Thread(target=self.login_process, daemon=True)
        self.login_thread.start()

    def login_process(self):
        while self.running:
            try:
                sleep(0.1)
                p = self.get_packets(["login_username", "final_login"])
                for packet in p:
                    if packet["type"] == "login_username":
                        username = packet.get("username")
                        if self.user_data.is_user(username) and username != self.serverName:
                            reset_password = self.user_data.get_user_data(username, "reset_password", False)
                            if reset_password:
                                self.user_data.change_user_salt(username)
                            alg, salt = self.user_data.get_hash_and_salt(username)
                            self.obj.send_packet({"type": "login_alg_and_salt", "alg": alg, "salt": salt,
                                                  "reset_password": reset_password})
                        else:
                            self.obj.send_packet({"type": "login_alg_and_salt", "alg": self.user_data.get_latest_hash(),
                                                  "salt": self.user_data.generate_random_string(),
                                                  "reset_password": False})
                    elif packet["type"] == "final_login":
                        username = packet.get("username")
                        hash_ = packet.get("hash")
                        if self.user_data.get_user_data(username, "reset_password", False):
                            alg, salt = self.user_data.get_hash_and_salt(username)
                            self.user_data.update_user_password(username, hash_=hash_, salt=salt, hash_alg=alg)
                            self.user_data.set_user_data(username, "reset_password", False)
                            self.username = username
                            self.running = False
                            self.obj.send_packet({"type": "login_response", "response": "success"})
                            self.manager.print_all(f"Got connection from {self.username}")

                        elif self.user_data.login_user(username, password_hash=hash_):
                            self.running = False
                            self.username = username
                            self.load_data()
                            self.obj.send_packet({"type": "login_response", "response": "success"})
                            self.manager.print_all(f"Got connection from {self.username}")

                        else:
                            self.obj.send_packet({"type": "login_response", "response": "failure"})
            except Exception as e:
                self.print(str(e))

    def load_data(self):
        self.logged_in = True
        filter_data = self.user_data.get_user_data(self.username, "filter_data")
        if filter_data:
            self.filters = filter_data.get("filters", self.filters)
            self.default_filter_behavior = filter_data.get("default", self.default_filter_behavior)
            self.filter_enabled = filter_data.get("enabled", self.filter_enabled)

    def set_filter(self, enable):
        self.filter_enabled = enable

    def modify_filter(self, enabled, controller="", instance=""):
        if not controller:
            return False
        if not instance:
            self.filters["controllers"][controller] = enabled
            return True
        full_path = controller+"/"+instance
        self.filters["instances"][full_path] = enabled
        return True

    def get_filter(self):
        return self.filters

    def set_filter_default(self, enable):
        self.default_filter_behavior = enable

    def get_filter_default(self):
        return self.default_filter_behavior

    def reset_filter(self):
        self.filters = {"controllers": {}, "instances": {}}

    def is_filtered(self):
        return self.filter_enabled

    def check_filter(self, focus):
        allow = self.default_filter_behavior
        allow = self.filters["controllers"].get(focus[0], allow)
        if not focus[1]:
            return allow
        full_path = "/".join(focus)
        allow = self.filters["instances"].get(full_path, allow)
        return allow

    def is_focused(self):
        return self.focus != ("", "")

    def check_focus(self, focus):
        return (self.focus == focus) or (not self.focus[1] and self.focus[0] == focus[0])

    def update(self):
        if self.logged_in and not self.server:
            packets = self.get_packets(["change_password"])
            for p in packets:
                if p["type"] == "change_password":
                    if self.user_data.update_user_password(self.username, hash_=p["hash"],
                                                           salt=p["salt"], hash_alg=p["alg"]):
                        self.print("Successfully changed password.")
                    else:
                        self.print("Failed to change password")

    def print(self, data, newline=True, loop=True):
        if self.server:
            self.obj.print(data, newline=newline, loop=loop)
        else:
            self.obj.send_packet({"type": "text", "newline": newline, "loop": loop, "text": f"{data}"})

    def get_input(self):
        focus_prefix = ""
        if self.focus[0]:
            focus_prefix += "/" + self.focus[0]
        if self.focus[1]:
            focus_prefix += "/" + self.focus[1]
        if focus_prefix:
            focus_prefix += ":"
        if self.server:
            return [focus_prefix + i for i in self.obj.get_input()]
        return [(focus_prefix + i.get("text")) for i in self.get_packets("text")]

    def get_username(self):
        if self.server:
            return self.serverName
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
        start_time = time()
        while True:
            packets = self.get_packets(type_)
            if len(packets) > 0:
                return packets
            if timeout != -1 and start_time + timeout < time():
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

    def set_focus(self, module_name="", controller=""):
        self.focus = (module_name, controller)
        if not self.focus[0]:
            self.set_prefix(self.default_prefix)
        else:
            if self.focus[1]:
                self.set_prefix(f"/{self.focus[0]}/{self.focus[1]}:")
            else:
                self.set_prefix(f"/{self.focus[0]}:")

    def get_focus(self):
        return self.focus

    def set_prefix(self, prefix):
        if self.server:
            self.obj.update_prefix(prefix)
        else:
            self.obj.send_packet({"type": "update_prefix", "text": prefix})

    def get_obj(self):
        return self.obj

    def get_id(self):
        return self.id

    def kick(self):
        if not self.server:
            self.obj.close()

    def exit(self):
        self.running = False
        if not self.server:
            filter_data = {"filters": self.filters,
                           "default": self.default_filter_behavior,
                           "enabled": self.filter_enabled}
            self.user_data.set_user_data(self.username, "filter_data", filter_data)
