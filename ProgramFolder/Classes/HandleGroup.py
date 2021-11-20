from .UserHandle import BufferUserHandle
import time


class HandleGroup:
    def __init__(self, server_handles, user_data, single_user=False):
        self.server_handles = server_handles
        self.user_data = user_data
        self.handles = {}  # {username: [{"id": id, "time": time, "handle": handle "data":{}}, {} . . .]}
        self.single_user = single_user

        self.timeout = -1

    def set_timeout(self, timeout):
        self.timeout = timeout

    def get_unused_id(self, username):
        if username not in self.handles:
            return 0
        used_ids = [i["id"] for i in self.handles[username]]
        for test_id in range(len(used_ids)):
            if test_id not in used_ids:
                return test_id
        return len(used_ids) + 1

    def create_handle(self, username):
        if self.single_user and username in self.handles:
            return self.find_handle(username)
        handle = BufferUserHandle(self.user_data, username, 0)
        if self.single_user:
            id_ = 0
            time_ = 0
        else:
            id_ = self.get_unused_id(username)
            time_ = time.time()
        handle.set_exit_callback(lambda: self.remove_handle(username, (id_, time_)))
        h = {"id": id_, "time": time_, "handle": handle, "last_time": time_, "username": username}
        if username not in self.handles:
            self.handles[username] = []
        self.handles[username].append(h)
        self.server_handles.append(handle)
        return h

    def find_handle(self, username, id_pair=None):
        if not id_pair:
            id_pair = (0, 0)
        if username not in self.handles:
            return None
        for handle in self.handles[username]:
            if handle["id"] == id_pair[0]:
                if handle["time"] == id_pair[1]:
                    return handle
                return None
        return None

    def get_handle(self, username, id_pair=None):
        if not id_pair:
            id_pair = (0, 0)
        h = self.find_handle(username, id_pair)
        if h:
            return h
        return self.create_handle(username)

    def remove_handle(self, username, id_pair=None):
        if not id_pair:
            id_pair = (0, 0)
        h = self.find_handle(username, id_pair)
        if h:
            h["handle"].exit()
            if h in self.handles[username]:
                self.handles[username].remove(h)
            if h["handle"] in self.server_handles:
                self.server_handles.remove(h["handle"])

    def update_time(self, username, id_pair=None):
        if not id_pair:
            id_pair = (0, 0)
        h = self.find_handle(username, id_pair)
        if h:
            h["last_time"] = time.time()

    def get_time(self, username, id_pair=None):
        if not id_pair:
            id_pair = (0, 0)
        h = self.find_handle(username, id_pair)
        if h:
            return h["last_time"]
        return -1

    def close_all(self):
        for username in self.handles:
            for h in self.handles[username]:
                self.remove_handle(username, (h["id"], h["time"]))

    def get_all_handles(self):
        out = []
        for username in self.handles:
            for h in self.handles[username]:
                out.append(h)
        return out

    def check_for_timeouts(self):
        if self.timeout == -1:
            return
        current_time = time.time()
        for h in self.get_all_handles():
            t = h["last_time"]
            if t and t + self.timeout < current_time:
                h["handle"].exit()
