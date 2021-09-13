from json import dumps, loads
from hashlib import sha256
from random import choice
from string import ascii_letters
from time import time
from os import path


class UserData:
    def __init__(self):
        self.file_path = None
        self.users = {}
        self.latest_hash = "sha256"
        self.hashes = ["sha256"]

    def set_file_path(self, path_):
        self.file_path = path_
        if not path.isfile(self.file_path):
            return self.save()
        return True

    def save(self):
        try:
            data = dumps(self.users)
            file = open(self.file_path, "w")
            file.write(data)
            file.close()
        except IOError:
            return False
        return True

    def load(self):
        try:
            file = open(self.file_path, "r")
            data = file.read()
            file.close()
            self.users = loads(data)
        except IOError:
            return False
        return True

    def get_user_data(self, username, key):
        if username in self.users:
            return self.users[username]["data"].get(key)
        return

    def set_user_data(self, username, key, value):
        if username in self.users:
            self.users[username]["data"][key] = value
            return True
        return False

    def get_users(self):
        return list(self.users.keys())

    def is_user(self, username):
        return username in self.users

    def get_hash_and_salt(self, username):
        if username in self.users:
            u = self.users[username]
            return u["hash_type"], u["salt"]

    def login_user(self, username, password=None, password_hash=None):
        if username in self.users and (password or password_hash):
            u = self.users[username]
            if password_hash:
                return self.secure_compare(password_hash, u["hash"])
            else:
                return self.secure_compare(self.generate_hash(u["salt"] + password, u["hash_type"]), u["hash"])
        return False

    def update_user_password(self, username, hash_=None, salt=None, hash_alg=None, password=None):
        if username not in self.users:
            return False
        if not hash_alg:
            hash_alg = self.get_latest_hash()
        if not salt:
            salt = self.generate_random_string()

        if password:
            hash_ = self.generate_hash(salt + password, hash_alg)
        if not hash_:
            return False

        self.users[username]["hash"] = hash_
        self.users[username]["salt"] = salt
        self.users[username]["hash_type"] = hash_alg
        self.users[username]["time"] = str(time())
        return True

    def get_password_time(self, username):
        if username not in self.users:
            return -1
        return int(self.users[username]["time"])

    def check_hash_secure(self, username):
        if username in self.users:
            return self.get_latest_hash() == self.users[username]["hash_type"]
        return False

    def create_user(self, username, hash_=None, salt=None, hash_alg=None, password=None):
        if username in self.users:
            return False
        self.users[username] = {"data": {}}
        return self.update_user_password(username, hash_, salt, hash_alg, password)

    def remove_user(self, username):
        if username not in self.users:
            return False
        del self.users[username]
        return True

    def get_hashes(self):
        return self.hashes

    def get_latest_hash(self):
        return self.latest_hash

    @staticmethod
    def secure_compare(a, b):
        correct = True
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                correct = False
        return correct and (len(a) == len(b))

    @staticmethod
    def generate_hash(data, hash_type):
        if isinstance(data, type("")):
            data = data.encode()

        h = None

        if hash_type.lower() == "sha256":
            m = sha256()
            m.update(data)
            h = m.hexdigest()

        return h

    @staticmethod
    def generate_random_string(length=5):
        return ''.join(choice(ascii_letters) for _ in range(length))
