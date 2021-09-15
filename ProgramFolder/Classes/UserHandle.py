class UserHandle:
    def __init__(self, obj, server=False):
        self.obj = obj
        self.server = server

    def print(self, data, newline=True, loop=True):
        if self.server:
            self.obj.print(data, newline=newline, loop=loop)

    def get_input(self):
        if self.server:
            return self.obj.get_input()