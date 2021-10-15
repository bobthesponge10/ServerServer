from Classes import BaseController
from requests import get
from os import path as ospath
from os import chdir, getcwd
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
from json import loads


class Controller(BaseController):
    type = "Minecraft"

    def __init__(self, *args):
        super().__init__(*args)

        self.thread = None
        self.process = None

        self.env_manager = self.manager.get_env_manager()

        self.minecraft_jar_versions = []
        self.load_minecraft_jar_versions()

        if len(args) >= 4:
            self.version = args[3]
        else:
            self.set_version_to_latest()

        self.jar_name = "server.jar"
        self.memory_to_use = 4096
        self.world_file = "world"
        self.port = 25565

        if not self.get_data():
            self.save_data()
        else:
            self.data = self.get_data()
            self.port = self.data.get("port", self.port)
            self.jar_name = self.data.get("jar_name", self.jar_name)
            self.world_file = self.data.get("world_file", self.world_file)
            self.version = self.data.get("version", self.version)
            self.memory_to_use = self.data.get("memory_to_use", self.memory_to_use)
        self.port = self.port_handler.request_port(self.port)

        self.set_address(f"{self.port_handler.get_ip()}:{self.port}")

        self.property_file_name = "server.properties"

    def save_data(self):
        self.data = {"port": self.port,
                     "jar_name": self.jar_name,
                     "world_file": self.world_file,
                     "version": self.version,
                     "memory_to_use": self.memory_to_use}
        self.set_data(self.data)

    def run(self, just_setup=False):
        try:
            self.running = True
            self.initial_setup()
            if not just_setup:
                self.run_server()
            self.running = False
        except Exception as e:
            self.running = False
            self.add_to_queue("Error running server:" + str(e))

    def run_server(self):
        java_path = self.get_java_path()
        old_dir = ospath.abspath(getcwd())
        chdir(self.path)
        self.add_to_queue(f"Starting server at port: {self.port}")
        self.process = Popen(
            f"{java_path} -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} nogui",
            stdin=PIPE, stdout=PIPE, stderr=PIPE)
        chdir(old_dir)
        poll = self.process.poll()

        while poll is None:
            sleep(0.1)
            out = self.process.stdout.readline().decode()
            out = out.replace("\n", "")
            if len(out) > 0:
                self.add_to_queue(out)
            poll = self.process.poll()
        self.add_to_queue("Server Closed")
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()
        self.process = None

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

    def initial_setup(self):
        java_path = self.get_java_path()
        old_dir = ospath.abspath(getcwd())
        if not ospath.isfile(ospath.join(self.path, self.jar_name)):
            self.add_to_queue("Jar file missing")
            if not self.download_jar():
                return False

        self.write_properties()

        if not ospath.isfile(ospath.join(self.path, "eula.txt")):
            self.add_to_queue("Running setup for eula")
            chdir(self.path)
            self.process = Popen(
                f"{java_path} -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} nogui",
                stdin=PIPE, stdout=PIPE, stderr=PIPE)
            chdir(old_dir)
            self.process.stdin.write(b"stop\n")
            self.process.stdin.flush()
            self.process.communicate()
            if self.process.poll() != 0:
                self.add_to_queue("Error running jar file, is the correct version of java installed?")
                self.process = None
                return False
            self.process = None

        if ospath.isfile(ospath.join(self.path, "eula.txt")):
            eula = open(ospath.join(self.path, "eula.txt"), "r")
            data = eula.read()
            eula.close()
            if "eula=true" in data and ospath.isdir(self.world_file):
                chdir(old_dir)
                return
            self.add_to_queue("Editing eula")
            eula = open(ospath.join(self.path, "eula.txt"), "w")
            data = data.replace("eula=false", "eula=true")
            eula.write(data)
            eula.close()

        self.add_to_queue("Running initial setup")
        chdir(self.path)
        self.process = Popen(f"{java_path} -Xmx{self.memory_to_use}M -Xms{self.memory_to_use}M -jar {self.jar_name} "
                             f"nogui", stdin=PIPE, stdout=PIPE, stderr=PIPE)
        chdir(old_dir)
        self.process.stdin.write(b"stop\n")
        self.process.stdin.flush()
        self.process.communicate()
        self.process = None
        chdir(old_dir)
        self.add_to_queue("Finished initial setup")
        return True

    def write_properties(self):
        data = []
        out = []
        properties = {"server-port": self.port, "server-ip": self.port_handler.get_ip(), "level-name": self.world_file}
        if ospath.isfile(self.property_file_name):
            file = open(ospath.join(self.path, self.property_file_name), "r")
            data = file.read().split("\n")
            file.close()

        for line in data:
            spl = line.split("=")
            if len(spl) > 1:
                key = spl[0]
                val = spl[1]
                if key in properties:
                    val = properties[key]
                    del properties[key]
                out.append(f"{key}={val}")
            else:
                out.append(line)

        for key in properties:
            out.append(f"{key}={properties[key]}")

        data = "\n".join(out)

        file = open(ospath.join(self.path, self.property_file_name), "w")
        file.write(data)
        file.close()

    def get_download_url(self):
        list_ = [i for i in self.minecraft_jar_versions if i.get("id") == self.version]
        if len(list_) == 0:
            return None
        url = list_[0].get("url")
        if not url:
            return None
        raw = get(url).text
        j = loads(raw)
        server = j.get("downloads", {}).get("server")
        if not server:
            return None
        download_url = server.get("url")
        if not download_url:
            return None
        return download_url

    def download_jar(self):
        if not ospath.isfile(self.jar_name):
            self.add_to_queue("Downloading jar file")
            download_url = self.get_download_url()

            if not download_url:
                self.add_to_queue(f"Could not find server jar with version: {self.version}, "
                                  f"using latest version instead")
                self.set_version_to_latest()
                download_url = self.get_download_url()

            if not download_url:
                self.add_to_queue("Failed to download server")
                return False

            data = get(download_url).content
            if not data:
                self.add_to_queue("Failed to download server")
                return False
            try:
                file = open(ospath.join(self.path, self.jar_name), "wb")
                file.write(data)
                file.close()
            except IOError:
                self.add_to_queue("Failed to download server")
                return False
            return True

    def load_minecraft_jar_versions(self):
        raw = get("https://launchermeta.mojang.com/mc/game/version_manifest.json").text
        j = loads(raw)
        versions = j.get("versions")
        self.minecraft_jar_versions = versions

    def set_version_to_latest(self):
        raw = get("https://launchermeta.mojang.com/mc/game/version_manifest.json").text
        j = loads(raw)
        version = j.get("latest").get("release")
        self.version = version

    def get_java_path(self):
        if not self.env_manager.java_is_installed():
            self.add_to_queue("Installing java")
            if self.env_manager.install_java():
                self.add_to_queue("Java successfully installed")
            else:
                self.add_to_queue("Java failed to install")
        return self.env_manager.get_java_executor()

    @classmethod
    def init_commands(cls):
        super().init_commands()

        @cls.add_command(["mnc"])
        def t(self, user, *args):
            user.print("OOGA BOOGA")

        @cls.add_command(["_"])
        def start(self, user, *args):
            if not len(args) > 0:
                user.print("Error: no message given")
                return False
            if self.running and self.process:
                inp = " ".join(args)
                try:
                    self.process.stdin.write((inp + "\n").encode())
                    self.process.stdin.flush()
                except ValueError:
                    user.print("Error: server not running")
                    return False
                return True
            user.print("Error: server not running")
            return False
