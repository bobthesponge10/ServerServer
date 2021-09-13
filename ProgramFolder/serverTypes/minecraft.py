from _distutils_hack import override

from Classes import BaseController


class Controller(BaseController):
    name = "Minecraft"

    def __init__(self, name):
        super().__init__(name)

    @classmethod
    def init_commands(cls):
        super().init_commands()

        @cls.add_class_command(["say"])
        def start(self):
            pass
