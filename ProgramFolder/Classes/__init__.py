from .functions import install_requirements as __install_requirements
from os import path, chdir

chdir(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

__install_requirements("ProgramFolder/data/requirements.txt")

from .ConsoleUI import ConsoleUI
from .UserData import UserData
from .BaseController import BaseController
from .Server import Server
from .Client import Client
from .UserHandle import UserHandle
from .PortHandler import PortHandler
from .EnvManager import EnvManager
