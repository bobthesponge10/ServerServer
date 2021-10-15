from socket import socket, error
from select import select
from time import sleep
from pickle import dumps, load, HIGHEST_PROTOCOL, PickleError
from json import dumps as j_dumps
from json import loads as j_loads
from queue import Queue, Empty
from threading import Thread
from io import BytesIO


class Client(Thread):
    def __init__(self):
        super(Client, self).__init__()

        self.wait_time = 0.1

        self.port = 10000
        self.ip = "127.0.0.1"

        self.socket = socket()
        self.version = -2
        self.version_to_use = HIGHEST_PROTOCOL

        self.stopping = False
        self.running = False

        self.bytes = b""
        self.bytes_queue = Queue()

    def start(self):
        self.socket = socket()
        try:
            self.socket.connect((self.ip, self.port))

            version = int(self.socket.recv(1).decode())
            encoded = str(self.version_to_use).encode()
            if len(encoded) == 1:
                encoded += b" "
            self.socket.send(encoded)

            self.version = min(version, self.version_to_use)
            self.running = True
            super(Client, self).start()
        except error:
            pass

    def stop(self):
        self.stopping = True

    def run(self):
        running = self.running
        while running:
            if self.wait_time > 0:
                sleep(self.wait_time)
            if self.stopping:
                running = False
                try:
                    self.socket.shutdown(2)
                except error:
                    pass
                self.socket.close()
                continue
            try:
                read_sockets, write_sockets, error_sockets = select([self.socket], [], [], 0)
                for sock in read_sockets:
                    data = sock.recv(1024)
                    if len(data) == 0:
                        self.stopping = True
                    else:
                        self.add_bytes(data)
            except error:
                self.stopping = True
                continue
        self.running = False

    def send_packet(self, packet):
        try:
            if self.version != -1:
                self.socket.send(dumps(packet, protocol=self.version))
            else:
                self.socket.send(j_dumps(packet).encode() + b"\x00")
        except error:
            self.stopping = True

    def add_bytes(self, bytes_):
        self.bytes_queue.put(bytes_)

    def gather_bytes(self):
        while self.bytes_queue.qsize() > 0:
            try:
                self.bytes += self.bytes_queue.get(False)
            except Empty:
                break

    def get_packet(self):
        self.gather_bytes()
        if len(self.bytes) == 0:
            return None

        if self.version != -1:
            try:
                stream = BytesIO(self.bytes)
                decoded = load(stream)
                self.bytes = stream.read()
                stream.close()
                return decoded
            except (PickleError, EOFError):
                return None
        else:
            p = self.bytes.find(b"\x00")
            if p != -1:
                packet = self.bytes[:p]
                self.bytes = self.bytes[p + 1:]
                s = packet.decode()
                decoded = j_loads(s)
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

    def set_port(self, port):
        self.port = port

    def set_ip(self, ip):
        self.ip = ip

    def get_port(self):
        return self.port

    def get_ip(self):
        return self.ip

    def get_running(self):
        return self.running

    def get_stopping(self):
        return self.stopping
