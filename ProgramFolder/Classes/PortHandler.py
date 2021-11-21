import socket
import re
from urllib.parse import urlparse, urlunparse
import requests
from xml.dom.minidom import parseString, Document
import http.client
import time
import CloudFlare
import string


class CloudflareWrapper:
    def __init__(self):
        self.email = ""
        self.api_key = ""
        self.domain = ""
        self.base_domain = ""
        self.proxy_domain = ""
        self.cf = None

        self.connected = False
        self.attempting = False

    def ensure_connection(self):
        try:
            if self.cf:
                self.cf.zones.get()
            else:
                self.cf = CloudFlare.CloudFlare(email=self.email, token=self.api_key)
        except CloudFlare.exceptions.CloudFlareAPIError:
            self.cf = CloudFlare.CloudFlare(email=self.email, token=self.api_key)

    def ensure_dns_record(self, record):
        if not self.connected and not self.attempting:
            return False
        try:
            zone_info = self.cf.zones.get(params={'name': self.domain})[0]
            zone_id = zone_info.get("id")
            record["name"] = self.format(record.get("name"))
            dns_records = self.cf.zones.dns_records.get(zone_id)

            for r in dns_records:
                if r.get("type") == record.get("type") and r.get("name") == record.get("name") and \
                        r.get("content") == record.get("content"):
                    return True
            for r in dns_records:
                if r.get("name") == record.get("name").lower():
                    self.cf.zones.dns_records.delete(zone_id, r.get("id"))
                    break

            self.cf.zones.dns_records.post(zone_id, data=record)
            return True
        except CloudFlare.exceptions.CloudFlareAPIError:
            return False

    def delete_record(self, name, service=""):
        if not self.connected:
            return False
        try:
            zone_info = self.cf.zones.get(params={'name': self.domain})[0]
            zone_id = zone_info.get("id")

            dns_records = self.cf.zones.dns_records.get(zone_id)
            for r in dns_records:
                n = r.get("name")
                if (not service and n == name.lower()) or (service and n.startswith(f"_{service}") and n.endswith(name)):
                    self.cf.zones.dns_records.delete(zone_id, r.get("id"))
                    break
            return True
        except CloudFlare.exceptions.CloudFlareAPIError:
            return False

    def setup(self, email, api_key, domain, base_domain, public_ip):
        self.email = email
        self.api_key = api_key
        self.domain = domain
        self.base_domain = self.format_subdomain(base_domain)
        self.proxy_domain = self.format_subdomain(base_domain+"p")

        try:
            self.ensure_connection()
            self.attempting = True
            if not self.ensure_dns_record({"name": f"{self.base_domain}.{self.domain}",
                                           "type": "A",
                                           "content": public_ip}):
                self.cf = None
                self.connected = False
                self.attempting = False
                return False
            if not self.ensure_dns_record({"name": f"{self.proxy_domain}.{self.domain}",
                                           "type": "A",
                                           "content": public_ip,
                                           "proxied": True}):
                self.cf = None
                self.connected = False
                self.attempting = False
                return False
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            self.cf = None
            self.connected = False
            self.attempting = False
            return False

        self.connected = True
        return True

    def remove_setup_records(self):
        self.delete_record(f"{self.base_domain}.{self.domain}")
        self.delete_record(f"{self.proxy_domain}.{self.domain}")

    def get_domain(self):
        return self.domain

    def get_base_domain(self):
        return self.base_domain

    def get_base_domain_proxy(self):
        return self.proxy_domain

    def get_connected(self):
        return self.connected

    @staticmethod
    def format(s):
        out = ""
        for i in s:
            if i in string.ascii_letters or i in string.digits or i == "-" or i == "." or i == "_":
                out += i
        return out.lower()

    @staticmethod
    def format_subdomain(s):
        out = ""
        for i in s:
            if i in string.ascii_letters or i in string.digits or i == "-":
                out += i
        return out.lower()


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
        self.rules = []

        self.timeout = 5
        self.attempts = 5

        self.connected = False

    def get_connected(self):
        return self.connected

    def search(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        sock.sendto(self.ssdpRequest, (self.SSDP_ADDR, self.SSDP_PORT))
        try:
            resp = sock.recv(1000)
        except socket.timeout:
            self.connected = False
            return False

        resp = resp.decode()

        parsed = re.findall(r'(?P<name>.*?): (?P<value>.*?)\r\n', resp)

        location = list(filter(lambda x: x[0].lower() == "location", parsed))

        router_path = urlparse(location[0][1])
        self.url = router_path

        return True

    def get_path(self):
        if not self.url:
            for i in range(self.attempts):
                if self.search():
                    break
                time.sleep(0.5)
            if not self.url:
                self.connected = False
                return False

        request = requests.get(urlunparse(self.url))
        directory = request.text

        dom = parseString(directory)

        service_types = dom.getElementsByTagName('serviceType')

        path = None

        for service in service_types:
            if service.childNodes[0].data.find('WANIPConnection') > 0:
                path = service.parentNode.getElementsByTagName('controlURL')[0].childNodes[0].data
        self.path = path
        if self.path:
            self.connected = True
        else:
            self.connected = False

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
            ("NewRemoteHost", ""),
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
                d = info.firstChild
                if d:
                    data[info.nodeName] = d.data
            ports.append(data)
        self.rules = ports
        return ports


class PortHandler:
    all_ports = []
    ip = ""

    use_upnp = False
    use_cloudflare = False
    cloudflare = CloudflareWrapper()
    upnp = Upnp()

    upnp_update_timestamp = -1
    upnp_timeout_time = 60
    upnp_ports = []

    public_ip = ""

    def __init__(self):
        self.taken_ports = []

    def request_port(self, port, max_number=-1, description="",
                     TCP=False, UDP=False, subdomain_name="", srv_service="", proxy=False):
        if max_number == -1 or max_number > 65535:
            max_number = 65535

        self.update_upnp_ports()

        while True:
            if port > max_number:
                return -1
            if self.check_port_availability(port):
                self._add_port(port, description=description,
                               TCP=TCP, UDP=UDP, subdomain_name=subdomain_name, srv_service=srv_service,
                               proxy=proxy)
                return port
            port += 1

    def check_port_availability(self, port):
        if port in [i.get("port") for i in self.all_ports]:
            return False
        if port in self.upnp_ports:
            return False
        return True

    def _add_port(self, port, description="", TCP=False, UDP=False, subdomain_name="", srv_service="", proxy=False):
        subdomain_name = CloudflareWrapper.format_subdomain(subdomain_name)
        forwarded = False
        if self.use_upnp and self.upnp.get_connected() and (TCP or UDP):
            if TCP:
                forwarded = self.upnp.forward_port(port, "TCP", port, self.ip, "ServerServer-" + description)
            if UDP:
                forwarded = forwarded or self.upnp.forward_port(port, "UDP", port, self.ip,
                                                                "ServerServer-" + description)
        routed = False
        name = ""
        srv = False
        if forwarded and self.use_cloudflare and self.cloudflare.get_connected() and subdomain_name:
            name = f"{subdomain_name}.{self.cloudflare.get_domain()}"
            if proxy:
                base_domain = f"{self.cloudflare.get_base_domain_proxy()}.{self.cloudflare.get_domain()}"
            else:
                base_domain = f"{self.cloudflare.get_base_domain()}.{self.cloudflare.get_domain()}"
            if srv_service:
                if TCP:
                    r = {"type": "SRV", "name": f"_{srv_service}._tcp.{name}", "content": f"0\\{port}\\tt{base_domain}",
                         "data": {"service": f"_{srv_service}",
                                  "proto": "_tcp",
                                  "name": subdomain_name,
                                  "priority": "0",
                                  "weight": "0",
                                  "port": str(port),
                                  "target": base_domain}}
                    routed = routed or self.cloudflare.ensure_dns_record(r)
                    srv = srv or routed
                if UDP and not TCP:
                    r = {"type": "SRV", "name": f"_{srv_service}._udp.{name}", "content": f"0\\{port}\\tt{base_domain}",
                         "data": {"service": f"_{srv_service}",
                                  "proto": "_udp",
                                  "name": subdomain_name,
                                  "priority": "0",
                                  "weight": "0",
                                  "port": str(port),
                                  "target": base_domain}}
                    routed = routed or self.cloudflare.ensure_dns_record(r)
                    srv = srv or routed
            else:
                routed = self.cloudflare.ensure_dns_record({"type": "CNAME", "name": name, "content": base_domain})

        p = {"port": port,
             "forwarded": forwarded,
             "address": f"{self.public_ip}:{port}",
             "routed": routed,
             "domain": name,
             "srv": srv,
             "service": srv_service,
             "proxy": proxy,
             "parent": self}

        self.all_ports.append(p)
        self.taken_ports.append(p)

    def remove(self, delete=False):
        for i in self.taken_ports:
            self.remove_port(i.get("port"), full_port=i, delete=delete)

    def remove_port(self, port, full_port=None, delete=False):
        self.update_upnp_ports()

        if not full_port:
            for p in self.all_ports:
                if p.get("port") == port:
                    full_port = p

        if full_port:
            self.remove_port_connections(port, full_port, delete)

    @classmethod
    def remove_port_connections(cls, port, full_port=None, delete=False):
        if not full_port:
            for p in cls.all_ports:
                if p.get("port") == port:
                    full_port = p

        if full_port:
            full_port["parent"].taken_ports.remove(full_port)
            cls.all_ports.remove(full_port)

            for rule in cls.upnp.rules:
                if int(rule["NewInternalPort"]) == int(rule["NewExternalPort"]) == port and \
                        rule["NewPortMappingDescription"].startswith("ServerServer"):
                    cls.upnp.delete_port(rule["NewExternalPort"], rule["NewProtocol"])
            if delete and full_port.get("routed"):
                cls.cloudflare.delete_record(full_port.get("domain"), service=full_port.get("service"))

    @classmethod
    def get_connection_to_port(cls, port):
        for p in cls.all_ports:
            if p.get("port") == port:
                if not p.get("forwarded"):
                    return f"{cls.ip}:{port}"
                elif not p.get("routed"):
                    if cls.cloudflare.get_connected():
                        d = cls.cloudflare.get_base_domain()
                        if p.get("proxy"):
                            d = cls.cloudflare.get_base_domain_proxy()
                        return f"{d}.{cls.cloudflare.get_domain()}:{port}"
                    return f"{cls.public_ip}:{port}"
                else:
                    if p.get("srv"):
                        return f"{p.get('domain')}"
                    return f"{p.get('domain')}:{port}"
        return ""

    @classmethod
    def set_ip(cls, ip):
        cls.ip = ip

    @classmethod
    def get_ip(cls):
        return cls.ip

    @classmethod
    def set_use_upnp(cls, use_upnp):
        cls.use_upnp = use_upnp

    @classmethod
    def get_use_upnp(cls):
        return cls.use_upnp

    @classmethod
    def set_use_cloudflare(cls, use_cloudflare):
        cls.use_cloudflare = use_cloudflare

    @classmethod
    def get_use_cloudflare(cls):
        return cls.use_cloudflare

    @classmethod
    def wipe_ports(cls):
        if not cls.use_upnp:
            return
        cls.update_upnp_ports()
        for rule in cls.upnp.rules:
            if rule["NewPortMappingDescription"].startswith("ServerServer"):
                cls.upnp.delete_port(rule["NewExternalPort"], rule["NewProtocol"])
        cls.update_upnp_ports(force=True)

    @classmethod
    def update_upnp_ports(cls, force=False):
        t = time.time()
        if not cls.upnp.get_connected():
            cls.upnp_update_timestamp = t
            return
        if cls.use_upnp and (force or (cls.upnp_update_timestamp == -1 or
                                       t >= cls.upnp_update_timestamp + cls.upnp_timeout_time)):
            cls.upnp_update_timestamp = t
            cls.upnp.get_port_rules()
            cls.upnp_ports = [int(i["NewInternalPort"]) for i in cls.upnp.rules] + \
                             [int(i["NewExternalPort"]) for i in cls.upnp.rules]

    @classmethod
    def get_public_ip(cls):
        if not cls.public_ip:
            try:
                cls.public_ip = requests.get("https://api.ipify.org/").text
            except requests.exceptions.ConnectionError:
                cls.public_ip = ""

    @classmethod
    def initialize_upnp(cls):
        if cls.use_upnp and not cls.upnp.get_connected():
            cls.upnp.get_path()

    @classmethod
    def initialize_cloudflare(cls, email, api_key, domain, base_domain):
        cls.get_public_ip()
        if not cls.use_cloudflare or not cls.upnp.get_connected():
            return
        cls.cloudflare.setup(email, api_key, domain, base_domain, cls.public_ip)

    @classmethod
    def close_connections(cls, ports=True, cloudflare=True, delete=True):
        if ports:
            for port in cls.all_ports:
                cls.remove_port_connections(port.get("port"), full_port=port, delete=delete)
        if cloudflare:
            if cls.use_cloudflare and cls.cloudflare.get_connected():
                cls.cloudflare.remove_setup_records()
