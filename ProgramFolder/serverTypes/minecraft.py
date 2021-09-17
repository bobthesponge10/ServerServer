from Classes import BaseController
import requests
import re
import os
import subprocess
from threading import Thread
import time


class Controller(BaseController):
    type = "Minecraft"

    def __init__(self, name, *args):
        super().__init__(name, *args)

        self.thread = Thread(target=self.run, daemon=True)

        self.version = "1.16.4"
        self.jar_name = "server.jar"
        self.memory_to_use = 4096
        self.world_file = "world"

        self.process = None

    def run(self):
        self.running = True
        self.initial_setup()
        self.run_server()
        self.running = False

    def run_server(self):
        old_dir = os.path.abspath(os.getcwd())
        os.chdir(self.path)
        self.add_to_queue("Starting server")
        self.process = subprocess.Popen(f"java -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} nogui",
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        poll = self.process.poll()

        while poll is None:
            time.sleep(0.1)
            out = self.process.stdout.readline().decode()
            out = out.replace("\n", "")
            self.add_to_queue(out)
            poll = self.process.poll()
        self.add_to_queue("Server Closed")
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()
        os.chdir(old_dir)

    def start(self):
        if not self.running:
            self.thread.start()

    def stop(self):
        if self.running and self.process:
            self.process.stdin.write(b"stop\n")
            self.process.stdin.flush()

    def initial_setup(self):
        old_dir = os.path.abspath(os.getcwd())
        os.chdir(self.path)

        if not os.path.isfile(self.jar_name):
            self.add_to_queue("Jar file missing")
            self.download_jar()

        if not os.path.isfile("eula.txt"):
            self.add_to_queue("Running setup for eula")
            subprocess.check_output(f"java -jar {self.jar_name} nogui")

        eula = open("eula.txt", "r")
        data = eula.read()
        eula.close()
        if "eula=true" in data and os.path.isdir(self.world_file):
            os.chdir(old_dir)
            return
        self.add_to_queue("Editing eula")
        eula = open("eula.txt", "w")
        data = data.replace("eula=false", "eula=true")
        eula.write(data)
        eula.close()

        self.add_to_queue("Running initial setup")
        p = subprocess.Popen(f"java -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} nogui",
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.stdin.write(b"stop\n")
        p.stdin.flush()
        p.communicate()
        os.chdir(old_dir)
        self.add_to_queue("Finished setup")

    def download_jar(self):
        if not os.path.isfile(self.jar_name):
            self.add_to_queue("Downloading jar file")
            html = requests.get(f"https://mcversions.net/download/{self.version}").text
            a = re.search(r"<a.{0,300}? href=\"(?P<url>https.{0,500}?server.jar)\".{0,300}?>Download Server Jar</a>", html)
            download_url = a.groupdict()["url"]

            data = requests.get(download_url).content
            file = open(self.jar_name, "wb")
            file.write(data)
            file.close()

    @classmethod
    def init_commands(cls):
        super().init_commands()

        @cls.add_command(["_"])
        def start(self, user, *args):
            if not len(args) > 0:
                user.print("Error: no message given")
                return False
            if self.running and self.process:
                inp = " ".join(args)
                user.print(inp)
                self.process.stdin.write((inp + "\n").encode())
                self.process.stdin.flush()
                return True
            user.print("Error: server not running")
            return False