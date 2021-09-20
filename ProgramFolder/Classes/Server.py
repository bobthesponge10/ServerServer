import socket
import select
import time
import pickle
import json
from threading import Thread
try:
    import queue
except ImportError:
    import Queue as queue

import io


class ClientHandler:
    def __init__(self, id_, socket, address, version, server):
        self.id = id_
        self.socket = socket
        self.address = address
        self.version = version
        self.server = server

        self.bytes = b""
        self.bytes_queue = queue.Queue()

    def get_id(self):
        return self.id

    def get_socket(self):
        return self.socket

    def get_version(self):
        return self.version

    def get_addr(self):
        return self.address

    def send_packet(self, packet):
        try:
            if self.version != -1:
                self.socket.send(pickle.dumps(packet, protocol=self.version))
            else:
                self.socket.send(json.dumps(packet).encode() + b"\x00")
        except socket.error:
            self.close()

    def close(self):
        self.server.close_connection(self.id)

    def add_bytes(self, bytes):
        self.bytes_queue.put(bytes)

    def gather_bytes(self):
        while self.bytes_queue.qsize() > 0:
            try:
                self.bytes += self.bytes_queue.get(False)
            except queue.Empty:
                break

    def get_packet(self):
        self.gather_bytes()
        if len(self.bytes) == 0:
            return None

        if self.version != -1:
            try:
                stream = io.BytesIO(self.bytes)
                decoded = pickle.load(stream)
                self.bytes = stream.read()
                stream.close()
                return decoded
            except (pickle.PickleError, EOFError):
                return None
        else:
            p = self.bytes.find(b"\x00")
            if p != -1:
                packet = self.bytes[:p]
                self.bytes = self.bytes[p + 1:]
                s = packet.decode()
                decoded = json.loads(s)
                return decoded
            return None

    def get_all_packets(self):
        out = []
        while True:
            packet = self.get_packet()
            if packet:
                out.append(packet)
            else:
                break
        return out


class Server(Thread):
    def __init__(self, logger=None):
        super(Server, self).__init__()
        self.wait_time = 0.1
        self.pickle_encoding = pickle.HIGHEST_PROTOCOL

        self.stopping = False
        self.running = False
        self.current_id = 0
        self.clients = {}
        self.new_connections = queue.Queue()
        self.old_connections = queue.Queue()

        self.socket = socket.socket()
        self.port = 10000
        self.ip = "127.0.0.1"
        self.socket_list = []

        self.logger = logger

    def start(self):
        if not self.running:
            self.current_id = 0
            self.clients = {}

            self.new_connections.empty()
            self.old_connections.empty()

            self.socket = socket.socket()

            fails = 0
            while True:
                try:
                    self.socket.bind((self.ip, self.port))
                    break
                except:
                    if fails >= 10:
                        self.log("Failed socket bind " + str(fails) + " times, shutting down")
                        return
                    fails += 1
                    self.log("Failed socket bind, trying again")
                    time.sleep(1)
            self.socket.listen(10)

            self.update_sockets()

            self.running = True
            super(Server, self).start()

    def stop(self):
        self.stopping = True
        self.socket.close()
        for i in self.get_client_ids():
            self.clients[i].close()

    def run(self):
        running = self.running
        while running:
            if self.wait_time > 0:
                time.sleep(self.wait_time)
            if self.stopping:
                running = False
                self.socket.close()
                continue
            read_sockets, write_sockets, error_sockets = select.select(self.socket_list, [], [], 0)
            for sock in read_sockets:
                if sock == self.socket:
                    try:
                        new_socket, address = self.socket.accept()
                        new_socket.send(str(self.pickle_encoding).encode())
                        client_version = new_socket.recv(2).decode()
                        new_socket_version = int(client_version)
                    except socket.error:
                        continue

                    client = ClientHandler(self.current_id,
                                           new_socket,
                                           address,
                                           min(self.pickle_encoding, new_socket_version),
                                           self)
                    self.clients[self.current_id] = client
                    self.new_connections.put(client.get_id())
                    self.current_id += 1
                    self.update_sockets()
                else:
                    id_ = -1
                    data = b""
                    for ids in self.clients:
                        if self.clients[ids].get_socket:
                            id_ = ids
                    error = False
                    try:
                        data = sock.recv(1024)
                        if len(data) == 0:
                            error = True
                    except socket.error:
                        error = True
                    if error:
                        if id != -1:
                            self.close_connection(id_)
                            continue
                    if id_ != -1:
                        client = self.get_client_from_id(id_)
                        client.add_bytes(data)

        self.running = False

    def update_sockets(self):
        self.socket_list = [self.socket]
        for i in self.clients:
            self.socket_list.append(self.clients[i].get_socket())

    def get_client_ids(self):
        return list(self.clients.keys())

    def get_client_from_id(self, id_):
        if id_ in self.clients:
            return self.clients[id_]
        return None

    def set_port(self, port):
        self.port = port

    def set_ip(self, ip):
        self.ip = ip

    def get_port(self):
        return self.port

    def get_ip(self):
        return self.ip

    def get_new_connections(self):
        out = []
        while self.new_connections.qsize() > 0:
            try:
                out.append(self.new_connections.get(False))
            except queue.Empty:
                break
        return out

    def get_old_connections(self):
        out = []
        while self.old_connections.qsize() > 0:
            try:
                out.append(self.old_connections.get())
            except queue.Empty:
                break
        return out

    def close_connection(self, id_):
        if id_ in self.clients:
            self.old_connections.put(id_)
            client = self.clients[id_]
            try:
                client.socket.shutdown(2)
            except socket.error:
                pass
            client.socket.close()
            del self.clients[id_]
            self.update_sockets()

    def set_wait_time(self, t):
        self.wait_time = t

    def get_running(self):
        return self.running

    def log(self, string):
        if self.logger:
            self.logger(string)