import os
import platform
import requests
import shutil
from zipfile import ZipFile
import tarfile


class EnvManager:
    def __init__(self, env_path):
        self.env_path = env_path
        self.java_path = "java"
        self.java_exe_path = "bin/java"
        sys = platform.system()
        if sys == "Windows":
            self.java_exe_path += ".exe"

        self.temp_path = "temp"

    def get_env_path(self):
        return self.env_path

    def install_java(self):
        sys = platform.system()
        url = ""
        format = ""
        temp_dir = os.path.join(self.env_path, self.temp_path)
        temp_file = os.path.join(temp_dir, "temp_java")
        java_path = os.path.join(self.env_path, self.java_path)
        if os.path.isdir(java_path):
            shutil.rmtree(java_path)

        if not os.path.isdir(temp_dir):
            os.makedirs(temp_dir)
        if sys == "Windows":
            url = "https://download.oracle.com/java/17/latest/jdk-17_windows-x64_bin.zip"
            format = ".zip"
        elif sys == "Linux":
            url = "https://download.oracle.com/java/17/latest/jdk-17_linux-x64_bin.tar.gz"
            format = ".tar.gz"
        elif sys == "Darwin":
            url = "https://download.oracle.com/java/17/latest/jdk-17_macos-x64_bin.tar.gz"
            format = ".tar.gz"

        temp_file += format

        if not url:
            return False

        data = requests.get(url).content
        file = open(temp_file, "wb")
        file.write(data)
        file.close()

        if format == ".zip":
            z = ZipFile(temp_file)
            for member in z.namelist():
                base = os.path.basename(member)
                sep = member[-(len(base)+1)]
                p = os.path.sep.join(member.split(sep)[1:])
                if len(p) > 0 and p[-1] != os.path.sep:

                    d = os.path.sep.join(p.split(os.path.sep)[:-1])
                    d = os.path.join(java_path, d)
                    if not os.path.isdir(d):
                        os.makedirs(d)
                    source = z.open(member)
                    target = open(os.path.join(java_path, p), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

            z.close()
            os.remove(temp_file)
            return True
        elif format == ".tar.gz":
            t = tarfile.open(temp_file, "r:gz")
            for member in t.getnames():
                base = os.path.basename(member)
                sep = member[-(len(base) + 1)]
                p = os.path.sep.join(member.split(sep)[1:])
                if len(p) > 0 and p[-1] != os.path.sep:

                    d = os.path.sep.join(p.split(os.path.sep)[:-1])
                    d = os.path.join(java_path, d)
                    if not os.path.isdir(d):
                        os.makedirs(d)
                    source = t.extractfile(member)
                    target = open(os.path.join(java_path, p), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

            t.close()
            os.remove(temp_file)
        return False

    def java_is_installed(self):
        java_path = os.path.join(self.env_path, self.java_path, self.java_exe_path)
        return os.path.isfile(java_path)

    def get_java_executor(self):
        java_path = os.path.join(self.env_path, self.java_path, self.java_exe_path)
        if os.path.isfile(java_path):
            return os.path.abspath(java_path)
        return "java"
