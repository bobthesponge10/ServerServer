import socket
import re
from urllib.parse import urlparse, urlunparse
import requests
from xml.dom.minidom import parseString, Document
import http.client


class PortHandler:
    all_ports = []
    ip = ""

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

    @classmethod
    def set_ip(cls, ip):
        cls.ip = ip

    @classmethod
    def get_ip(cls):
        return cls.ip


class Upnp:
    def __init__(self):
        self.SSDP_ADDR = "239.255.255.250"
        self.SSDP_PORT = 1900
        self.SSDP_MX = 2
        self.SSDP_ST = "urn:schemas-upnp-org:device:InternetGatewayDevice:1"
        self.ssdpRequest = "M-SEARCH * HTTP/1.1\r\n" \
                           f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n" + \
                           "MAN: \"ssdp:discover\"\r\n" + \
                           f"MX: {self.SSDP_MX}\r\n" + \
                           f"ST: {self.SSDP_ST}\r\n" + "\r\n"
        self.ssdpRequest = self.ssdpRequest.encode()

        self.url = None
        self.path = ""

        self.search()
        self.get_path()

    def search(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(30)
        sock.sendto(self.ssdpRequest, (self.SSDP_ADDR, self.SSDP_PORT))
        resp = sock.recv(1000)
        resp = resp.decode()

        parsed = re.findall(r'(?P<name>.*?): (?P<value>.*?)\r\n', resp)

        location = list(filter(lambda x: x[0].lower() == "location", parsed))

        router_path = urlparse(location[0][1])
        self.url = router_path
        print(router_path)

    def get_path(self):
        if not self.url:
            self.search()
            if not self.url:
                return
        request = requests.get(urlunparse(self.url))
        directory = request.text

        dom = parseString(directory)

        service_types = dom.getElementsByTagName('serviceType')

        path = None

        for service in service_types:
            if service.childNodes[0].data.find('WANIPConnection') > 0:
                path = service.parentNode.getElementsByTagName('controlURL')[0].childNodes[0].data
        self.path = path
        print(path)

    @staticmethod
    def generate_xml(arguments, action):
        doc = Document()
        envelope = doc.createElementNS('', 's:Envelope')
        envelope.setAttribute('xmlns:s', 'http://schemas.xmlsoap.org/soap/envelope/')
        envelope.setAttribute('s:encodingStyle', 'http://schemas.xmlsoap.org/soap/encoding/')

        body = doc.createElementNS('', 's:Body')
        fn = doc.createElementNS('', f'u:{action}')
        fn.setAttribute('xmlns:u', 'urn:schemas-upnp-org:service:WANIPConnection:1')

        argument_list = []

        for k, v in arguments:
            tmp_node = doc.createElement(k)
            tmp_text_node = doc.createTextNode(v)
            tmp_node.appendChild(tmp_text_node)
            argument_list.append(tmp_node)

        for arg in argument_list:
            fn.appendChild(arg)

        body.appendChild(fn)

        envelope.appendChild(body)

        doc.appendChild(envelope)

        pure_xml = doc.toxml()
        return pure_xml

    def forward_port(self, external_port, protocol, internal_port, internal_client, desc="", lease_duration=0):
        if not self.path:
            self.get_path()
            if not self.path:
                return False

        arguments = [
            ('NewExternalPort', str(external_port)),
            ('NewProtocol', str(protocol)),
            ('NewInternalPort', str(internal_port)),
            ('NewInternalClient', str(internal_client)),
            ('NewEnabled', '1'),
            ('NewPortMappingDescription', str(desc)),
            ('NewLeaseDuration', str(lease_duration))]

        pure_xml = self.generate_xml(arguments, "AddPortMapping")

        conn = http.client.HTTPConnection(self.url.hostname, self.url.port)

        conn.request('POST',
                     self.path,
                     pure_xml,
                     {'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"',
                      'Content-Type': 'text/xml'}
                     )
        resp = conn.getresponse()
        return resp.status == 200

    def delete_port(self, external_port, protocol):
        if not self.path:
            self.get_path()
            if not self.path:
                return False

        arguments = [
            ('NewExternalPort', str(external_port)),
            ('NewProtocol', str(protocol)),
            ('NewRemoteHost', "")]

        pure_xml = self.generate_xml(arguments, "DeletePortMapping")

        conn = http.client.HTTPConnection(self.url.hostname, self.url.port)

        conn.request('POST',
                     self.path,
                     pure_xml,
                     {'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#DeletePortMapping"',
                      'Content-Type': 'text/xml'}
                     )

        resp = conn.getresponse()
        return resp.status == 200

    def get_port_rules(self):
        if not self.path:
            self.get_path()
            if not self.path:
                return False
        index = 0
        ports = []
        while True:
            arguments = [('NewPortMappingIndex', str(index))]

            pure_xml = self.generate_xml(arguments, "GetGenericPortMappingEntry")

            conn = http.client.HTTPConnection(self.url.hostname, self.url.port)

            conn.request('POST',
                         self.path,
                         pure_xml,
                         {'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#GetGenericPortMappingEntry"',
                          'Content-Type': 'text/xml'}
                         )

            resp = conn.getresponse()
            index += 1
            if resp.status != 200:
                break
            p = parseString(resp.read())

            port_info = p.getElementsByTagName('u:GetGenericPortMappingEntryResponse')[0]

            data = {}

            for info in port_info.childNodes:
                data[info.nodeName] = info.data


        return ports
