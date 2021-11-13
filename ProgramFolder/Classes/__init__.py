from .functions import install_requirements as __install_requirements
from os import path, chdir, getcwd
from sys import argv


old_dir = getcwd()
chdir(path.dirname(path.dirname(path.join(argv[0], __file__))))

__install_requirements("data/requirements.txt")
chdir(old_dir)

from .ConsoleUI import ConsoleUI
from .UserData import UserData
from .BaseController import BaseController
from .Server import Server
from .Client import Client
from .UserHandle import UserHandle
from .PortHandler import PortHandler
from .EnvManager import EnvManager
from .gui import GUI
