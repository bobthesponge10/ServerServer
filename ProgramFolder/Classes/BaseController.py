import inspect


class BaseController:
    commands = []
    class_commands = []
    objects = []
    manager = None

    # <editor-fold desc="Class Methods">
    @classmethod
    def get_objects(cls):
        return cls.objects

    @classmethod
    def set_objects(cls, objects):
        cls.objects = objects
        for i in cls.objects:
            i.set_parent_object(cls)

    @classmethod
    def remove_object(cls, obj):
        cls.objects.remove(obj)

    @classmethod
    def init_commands(cls):
        cls.commands = []

        @cls.add_class_command(["test"])
        def test_command(cls_):
            cls_.get_manager().get_console().print("TestSuccess")

    @classmethod
    def add_command(cls, keywords):
        def f(func):
            cls.commands.append({"keywords": keywords, "function": func})
            return func

        return f

    @classmethod
    def add_class_command(cls, keywords):
        def f(func):
            cls.class_commands.append({"keywords": keywords, "function": func})
            return func

        return f

    @classmethod
    def run_class_command(cls, name, *args, **kwargs):
        for i in cls.class_commands:
            if name.lower() in i["keywords"]:
                i["function"](cls, *args, **kwargs)
                return True
        return False

    @classmethod
    def set_manager(cls, manager):
        cls.manager = manager

    @classmethod
    def get_manager(cls):
        return cls.manager
    # </editor-fold>

    def __init__(self, name):
        self.parent_object = BaseController
        self.objects.append(self)
        self.name = name

    def remove(self):
        self.parent_object.remove(self)

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object

    def run_command(self, name, *args, **kwargs):
        for i in self.parent_object.commands:
            if name.lower() in i["keywords"]:
                i["function"](self, *args, **kwargs)
                return True
        return False
