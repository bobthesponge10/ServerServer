class PortHandler:
    all_ports = []

    def __init__(self):
        self.taken_ports = []

    def request_port(self, port, max_number=-1):
        if max_number == -1 or max_number > 65535:
            max_number = 65535

        if port not in self.all_ports:
            self._add_port(port)
            return port

        else:
            while True:
                port += 1
                if port > max_number:
                    return -1

                if port not in self.all_ports:
                    self._add_port(port)
                    return port

    def _add_port(self, p):
        self.all_ports.append(p)
        self.taken_ports.append(p)

    def remove(self):
        for i in self.taken_ports:
            self.all_ports.remove(i)