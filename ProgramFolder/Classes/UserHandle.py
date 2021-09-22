class UserHandle:
    def __init__(self, obj, server=False, id_=-1):
        self.obj = obj
        self.server = server
        self.id = id_

    def print(self, data, newline=True, loop=True):
        if self.server:
            self.obj.print(data, newline=newline, loop=loop)
        else:
            self.obj.send_packet({"type": "text", "newline": newline, "loop": loop, "text": f"{data}"})

    def get_input(self):
        if self.server:
            return self.obj.get_input()
        packets = self.obj.get_all_packets()
        return [i["text"] for i in packets if i["type"] == "text"]

    def is_server(self):
        return self.server

    def get_obj(self):
        return self.obj

    def get_id(self):
        return self.id
