from Classes import BaseController
import requests
import re
import os
import subprocess
import time


class Controller(BaseController):
    type = "Minecraft"

    def __init__(self, name, *args):
        super().__init__(name, *args)

        self.version = "1.16.4"
        self.jar_name = "server.jar"

    def start(self):
        self.initial_setup()

    def stop(self):
        pass

    def initial_setup(self):
        self.download_jar()
        old_dir = os.path.abspath(os.getcwd())
        os.chdir(self.path)

        if not os.path.isfile("eula.txt"):
            self.add_to_queue("Running setup")
            subprocess.check_output(f"java -jar {self.jar_name} nogui")

        self.add_to_queue("Editing eula")
        eula = open("eula.txt", "r")
        data = eula.read()
        eula.close()
        eula = open("eula.txt", "w")
        data = data.replace("eula=false", "eula=true")
        eula.write(data)
        eula.close()

        p = subprocess.Popen(f"java -Xmx4096M -Xms4096M -jar {self.jar_name} nogui", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        #p.stdin.write(b"stop\n")
        #p.stdin.flush()
        p.communicate()
        os.chdir(old_dir)

    def download_jar(self):
        jar_file = os.path.join(self.path, self.jar_name)

        if not os.path.isfile(jar_file):
            self.add_to_queue("Downloading jar file")
            html = requests.get(f"https://mcversions.net/download/{self.version}").text
            a = re.search(r"<a.{0,300}? href=\"(?P<url>https.{0,500}?server.jar)\".{0,300}?>Download Server Jar</a>", html)
            download_url = a.groupdict()["url"]

            data = requests.get(download_url).content
            file = open(jar_file, "wb")
            file.write(data)
            file.close()

    @classmethod
    def init_commands(cls):
        super().init_commands()

        @cls.add_class_command(["say"])
        def start(cls, user, *args):
            user.print("said")
