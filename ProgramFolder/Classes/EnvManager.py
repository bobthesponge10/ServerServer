from os import path as ospath
from os import makedirs, remove
from platform import system
from requests import get, exceptions
from shutil import rmtree, copyfileobj
from zipfile import ZipFile
from tarfile import open as open_tar


class EnvManager:
    def __init__(self, env_path):
        self.env_path = env_path
        self.java_path = "java"
        self.java_exe_path = "bin/java"
        self.sys = system()
        if self.sys == "Windows":
            self.java_exe_path += ".exe"

        self.temp_path = "temp"

    def get_env_path(self):
        return self.env_path

    def install_java(self):
        url = ""
        format_ = ""
        temp_dir = ospath.join(self.env_path, self.temp_path)
        temp_file = ospath.join(temp_dir, "temp_java")
        java_path = ospath.join(self.env_path, self.java_path)
        if ospath.isdir(java_path):
            rmtree(java_path)

        if not ospath.isdir(temp_dir):
            makedirs(temp_dir)
        if self.sys == "Windows":
            url = "https://download.oracle.com/java/17/latest/jdk-17_windows-x64_bin.zip"
            format_ = ".zip"
        elif self.sys == "Linux":
            url = "https://download.oracle.com/java/17/latest/jdk-17_linux-x64_bin.tar.gz"
            format_ = ".tar.gz"
        elif self.sys == "Darwin":
            url = "https://download.oracle.com/java/17/latest/jdk-17_macos-x64_bin.tar.gz"
            format_ = ".tar.gz"

        temp_file += format_

        if not url:
            return False
        try:
            data = get(url).content
        except exceptions.ConnectionError:
            return False
        file = open(temp_file, "wb")
        file.write(data)
        file.close()

        if format_ == ".zip":
            z = ZipFile(temp_file)
            for member in z.namelist():
                base = ospath.basename(member)
                sep = member[-(len(base)+1)]
                p = ospath.sep.join(member.split(sep)[1:])
                if len(p) > 0 and p[-1] != ospath.sep:

                    d = ospath.sep.join(p.split(ospath.sep)[:-1])
                    d = ospath.join(java_path, d)
                    if not ospath.isdir(d):
                        makedirs(d)
                    source = z.open(member)
                    target = open(ospath.join(java_path, p), "wb")
                    with source, target:
                        copyfileobj(source, target)

            z.close()
            remove(temp_file)
            return True
        elif format_ == ".tar.gz":
            t = open_tar(temp_file, "r:gz")
            for member in t.getnames():
                base = ospath.basename(member)
                sep = member[-(len(base) + 1)]
                p = ospath.sep.join(member.split(sep)[1:])
                if len(p) > 0 and p[-1] != ospath.sep:

                    d = ospath.sep.join(p.split(ospath.sep)[:-1])
                    d = ospath.join(java_path, d)
                    if not ospath.isdir(d):
                        makedirs(d)
                    source = t.extractfile(member)
                    target = open(ospath.join(java_path, p), "wb")
                    with source, target:
                        copyfileobj(source, target)

            t.close()
            remove(temp_file)
            return True
        return False

    def java_is_installed(self):
        java_path = ospath.join(self.env_path, self.java_path, self.java_exe_path)
        return ospath.isfile(java_path)

    def get_java_executor(self):
        java_path = ospath.join(self.env_path, self.java_path, self.java_exe_path)
        if ospath.isfile(java_path):
            return ospath.abspath(java_path)
        return "java"
