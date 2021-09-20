from .functions import install_requirements as __install_requirements
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

__install_requirements("ProgramFolder/data/requirements.txt")

from .ConsoleUI import ConsoleUI
from .UserData import UserData
from .BaseController import BaseController
from .Server import Server
from .Client import Client
from .ControllerManager import ControllerManager
from .UserHandle import UserHandle
from .PortHandler import PortHandler