from json import dumps, loads
from hashlib import sha256
from random import choice
from string import ascii_letters
from time import time
from os import path
from typing import List, Tuple, Any


class UserData:
    """
    Class to handle all users data and login information securly.
    """
    def __init__(self):
        self.file_path = None
        self.users = {}
        self.latest_hash = "sha256"
        self.hashes = ["sha256"]

    def set_file_path(self, path_: str) -> bool:
        """
        Sets the path of the file that stores the user data.
        :param path_: The path of the file.
        :return: True or False if that file path was able to be written to.
        """
        self.file_path = path_
        if not path.isfile(self.file_path):
            return self.save()
        return True

    def get_file_path(self) -> str:
        """
        Returns the file path.
        :return: The path of the file.
        """
        return self.file_path

    def save(self) -> bool:
        """
        Saves the userdata to file.
        :return: True or False if the save was successful.
        """
        try:
            data = dumps(self.users)
            file = open(self.file_path, "w")
            file.write(data)
            file.close()
        except IOError:
            return False
        return True

    def load(self) -> bool:
        """
        Loads the userdata from file.
        :return: True or False if the load was successful.
        """
        try:
            file = open(self.file_path, "r")
            data = file.read()
            file.close()
            self.users = loads(data)
        except IOError:
            return False
        return True

    def get_user_data(self, username: str, key: str, default: object = None) -> object:
        """
        Gets a piece of data from user using a key.
        :param username: The user to retrieve data from.
        :param key: The key that determines what piece of data to get from the user.
        :param default: This value is returned if either the user or piece of data could not be found
        :return: Either the piece of data requested or the default value.
        """
        if username in self.users:
            return self.users[username]["data"].get(key, default)
        return default

    def set_user_data(self, username: str, key: str, value: object) -> bool:
        """
        Saves a piece of data to the user with a key.
        :param username: The user to save the data to.
        :param key: The key where the value should be saved.
        :param value: The value to be written to the key.
        :return: True or False if the value was successfully set.
        """
        if username in self.users:
            self.users[username]["data"][key] = value
            return True
        return False

    def get_users(self) -> List[str]:
        """
        Gets a list of all the users.
        :return: A list of all the users.
        """
        return list(self.users.keys())

    def is_user(self, username: str) -> bool:
        """
        Returns boolean representing if user exists.
        :return:
        """
        return username in self.users

    def change_user_salt(self, username: str) -> bool:
        """
        Changes a user's password's salt to a random value.
        :param username: The username to use.
        :return: A boolean if the value was able to be changed.
        """
        if username in self.users:
            u = self.users[username]
            u["salt"] = self.generate_random_string()
            return True
        return False

    def get_hash_and_salt(self, username: str) -> Tuple[str, str]:
        """
        Gets both the hash type and salt for the given user.
        :param username: The username to get the data from.
        :return: A tuple containing both the hash type and salt for the user if the user exists.
        """
        if username in self.users:
            u = self.users[username]
            return u["hash_type"], u["salt"]
        return "", ""

    def login_user(self, username: str, password: str = None, password_hash: str = None) -> bool:
        """
        Checks if user login info is correct.
        :param username: The username to login.
        :param password: The password to try to login with (Less secure, use hash instead).
        :param password_hash: The hash of the password and salt to try to login with.
        :return: True if login was successful, False otherwise.
        """
        if username in self.users and (password or password_hash):
            u = self.users[username]
            if password_hash:
                return self.secure_compare(password_hash, u["hash"])
            else:
                return self.secure_compare(self.generate_hash(u["salt"] + password, u["hash_type"]), u["hash"])
        return False

    def update_user_password(self, username: str, hash_: str = None, salt: str = None, hash_alg: str = None,
                             password: str = None) -> bool:
        """
        Changes the given users password.
        :param username: The user to change the password for.
        :param hash_: The hash of the password to save.
        :param salt: The salt used in the password hash.
        :param hash_alg: The algorithm used to hash the password.
        :param password: The raw password (Less secure, use hash instead).
        :return: True if update was successful, False otherwise.
        """
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

    def get_password_time(self, username: str) -> int:
        """
        Gets the time in seconds since the password was changed for a given user.
        :param username: The user to get the data from.
        :return: Integer time in seconds since password was changed.
        """
        if username not in self.users:
            return -1
        return int(self.users[username]["time"])

    def check_hash_secure(self, username: str) -> bool:
        """
        Checks if the given user's password is stored in the most recent hashing method.
        :param username: The user to check.
        :return: True if password is using the most recent hashing method, False otherwise.
        """
        if username in self.users:
            return self.get_latest_hash() == self.users[username]["hash_type"]
        return False

    def create_user(self, username: str, hash_: str = None, salt: str = None, hash_alg: str = None,
                    password: str = None) -> bool:
        """
        Creates a user from a username and password info.
        :param username: The username to use for user creation.
        :param hash_: The hash of the password to use.
        :param salt: The salt used to generate the password hash.
        :param hash_alg: The algorithm used to generate the password hash.
        :param password: The raw text password to use as a password. (Raw password is not saved, a hash is generated)
        :return: True if user was successfully created, False otherwise.
        """
        if username in self.users:
            return False
        self.users[username] = {"data": {}}
        return self.update_user_password(username, hash_, salt, hash_alg, password)

    def remove_user(self, username: str) -> bool:
        """
        Removes a user from a given username
        :param username: Username to use.
        :return: True if user was successfully removed, False otherwise.
        """
        if username not in self.users:
            return False
        del self.users[username]
        return True

    def get_hashes(self) -> List[str]:
        """
        Gets a list of supported hashing algorithms.
        :return: A list of supported hashing algorithms.
        """
        return self.hashes

    def get_latest_hash(self) -> str:
        """
        Gets the most secure hashing algorithm available.
        :return: The string representing the most secure hash algorithm available.
        """
        return self.latest_hash

    @staticmethod
    def secure_compare(a: Any, b: Any) -> bool:
        """
        A more secure compare that cannon be used for timing attacks.
        :param a: iterable object to compare.
        :param b: iterable object to compare.
        :return: True if a and b are equal.
        """
        correct = True
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                correct = False
        return correct and (len(a) == len(b))

    @staticmethod
    def generate_hash(data: Any, hash_type: str) -> str:
        """
        Generates hex of hash with given data and hashing algorithm.
        :param data: The data to be hashed
        :param hash_type: The string representation of the hash algorithm.
        :return: The hex digest of the hash.
        """
        if isinstance(data, str):
            data = data.encode()

        h = None

        if hash_type.lower() == "sha256":
            m = sha256()
            m.update(data)
            h = m.hexdigest()

        return h

    @staticmethod
    def generate_random_string(length: int = 5) -> str:
        """
        Generates a random string with given length.
        :param length: The length the string should be.
        :return: The random string.
        """
        return ''.join(choice(ascii_letters) for _ in range(length))
