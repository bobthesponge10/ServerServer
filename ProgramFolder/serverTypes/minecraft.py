from Classes import BaseController
import requests
import os
import subprocess
from threading import Thread
import time
import json


class Controller(BaseController):
    type = "Minecraft"

    def __init__(self, *args):
        super().__init__(*args)

        self.thread = None
        self.process = None

        self.minecraft_jar_versions = []
        self.load_minecraft_jar_versions()

        if len(args) > 0:
            self.version = args[0]
        else:
            self.set_version_to_latest()

        self.jar_name = "server.jar"
        self.memory_to_use = 4096
        self.world_file = "world"
        self.port = self.port_handler.request_port(25565)

        if not self.get_data():
            self.save_data()
        else:
            self.data = self.get_data()
            self.port = self.port_handler.request_port(self.data.get("port", self.port))
            self.jar_name = self.data.get("jar_name", self.jar_name)
            self.world_file = self.data.get("world_file", self.world_file)
            self.version = self.data.get("version", self.version)
            self.memory_to_use = self.data.get("memory_to_use", self.memory_to_use)

        self.property_file_name = "server.properties"
        self.add_to_queue(self.port)

    def save_data(self):
        self.data = {"port": self.port,
                     "jar_name": self.jar_name,
                     "world_file": self.world_file,
                     "version": self.version,
                     "memory_to_use": self.memory_to_use}
        self.set_data(self.data)

    def run(self, just_setup=False):
        self.add_to_queue(self.version)
        try:
            self.running = True
            self.initial_setup()
            if not just_setup:
                self.run_server()
            self.running = False
        except Exception as e:
            self.add_to_queue(str(e))

    def run_server(self):
        old_dir = os.path.abspath(os.getcwd())
        os.chdir(self.path)
        self.add_to_queue("Starting server")
        self.process = subprocess.Popen(
            f"java -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} nogui",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        poll = self.process.poll()

        while poll is None:
            time.sleep(0.1)
            out = self.process.stdout.readline().decode()
            out = out.replace("\n", "")
            if len(out) > 0:
                self.add_to_queue(out)
            poll = self.process.poll()
        self.add_to_queue("Server Closed")
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()
        os.chdir(old_dir)

    def start(self):
        if not self.running:
            self.thread = Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        if self.running and self.process:
            self.process.stdin.write(b"stop\n")
            self.process.stdin.flush()

    def setup(self):
        if not self.running:
            self.thread = Thread(target=self.run, args=(True,), daemon=True)
            self.thread.start()

    def initial_setup(self):  # TODO: Handle any failure that may occur when setting up server
        old_dir = os.path.abspath(os.getcwd())
        os.chdir(self.path)

        base_properties = {"server-port": self.port, "level-name": self.world_file}

        if not os.path.isfile(self.jar_name):
            self.add_to_queue("Jar file missing")
            self.download_jar()

        file = open(self.property_file_name, "w")
        data = []
        for i in base_properties:
            data.append(i + "=" + str(base_properties[i]))
        file.write("\n".join(data))
        file.close()

        if not os.path.isfile("eula.txt"):
            self.add_to_queue("Running setup for eula")
            sp = subprocess.Popen(
                f"java -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} nogui",
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sp.stdin.write(b"stop\n")
            sp.stdin.flush()
            sp.communicate()

        if os.path.isfile("eula.txt"):
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
        self.add_to_queue("Finished initial setup")

    def download_jar(self):
        if not os.path.isfile(self.jar_name):
            self.add_to_queue("Downloading jar file")
            url = [i for i in self.minecraft_jar_versions if i.get("id") == self.version][0].get("url")
            raw = requests.get(url).text
            j = json.loads(raw)

            server = j.get("downloads", {}).get("server")
            if not server:
                self.add_to_queue(f"Could not find server jar with version: {self.version}, "
                                  f"using latest version instead")
                self.set_version_to_latest()
                url = [i for i in self.minecraft_jar_versions if i.get("id") == self.version][0].get("url")
                raw = requests.get(url).text
                j = json.loads(raw)
                server = j.get("downloads", default={}).get("server")
                if not server:
                    self.add_to_queue("Failed to download server")
                    return False

            download_url = server.get("url")
            if not download_url:
                self.add_to_queue("Failed to download server")
                return False

            data = requests.get(download_url).content
            if not data:
                self.add_to_queue("Failed to download server")
                return False
            try:
                file = open(self.jar_name, "wb")
                file.write(data)
                file.close()
            except IOError:
                self.add_to_queue("Failed to download server")
                return False

    def load_minecraft_jar_versions(self):
        raw = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").text
        j = json.loads(raw)
        versions = j.get("versions")
        self.minecraft_jar_versions = versions

    def set_version_to_latest(self):
        raw = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").text
        j = json.loads(raw)
        version = j.get("latest").get("release")
        self.version = version

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
                self.process.stdin.write((inp + "\n").encode())
                self.process.stdin.flush()
                return True
            user.print("Error: server not running")
            return False
