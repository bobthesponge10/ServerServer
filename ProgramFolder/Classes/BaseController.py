from functions import remove_chars


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
    def add_command(cls, keywords, ignore_chars=None):
        if not ignore_chars:
            ignore_chars = []

        def f(func):
            cls.commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars})
            return func

        return f

    @classmethod
    def add_class_command(cls, keywords, ignore_chars=None):
        if not ignore_chars:
            ignore_chars = []

        def f(func):
            cls.class_commands.append({"keywords": keywords, "function": func, "ignore": ignore_chars})
            return func

        return f

    @classmethod
    def run_class_command(cls, name, *args, **kwargs):
        for i in cls.class_commands:
            temp_name = remove_chars(name, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                try:
                    i["function"](cls, *args, **kwargs)
                    return True
                except Exception as e:
                    cls.manager.get_console().print(f"Error running {name}, Error: {e.__repr__()}")
                    return False
        return False

    @classmethod
    def set_manager(cls, manager):
        cls.manager = manager

    @classmethod
    def get_manager(cls):
        return cls.manager
    # </editor-fold>
    # <editor-fold desc="Commands">

    @classmethod
    def init_commands(cls):
        cls.commands = []

        @cls.add_class_command(["test"])
        def test_command(cls_):
            cls_.get_manager().get_console().print("TestSuccess")
    # </editor-fold>

    def __init__(self, name):
        self.parent_object = BaseController
        self.objects.append(self)
        self.name = name

        self.data = None

    def remove(self):
        self.parent_object.remove(self)

    def set_parent_object(self, parent_object):
        self.parent_object = parent_object

    def set_data(self, data):
        self.data = data

    def get_data(self):
        return self.data

    def get_name(self):
        return self.name

    def run_command(self, name, *args, **kwargs):
        for i in self.parent_object.commands:
            temp_name = remove_chars(name, i["ignore"])
            if temp_name.lower() in i["keywords"]:
                try:
                    i["function"](self, *args, **kwargs)
                    return True
                except Exception as e:
                    self.parent_object.manager.get_console().print(f"Error running {name}, Error: {e.__repr__()}")
                    return False
        return False
