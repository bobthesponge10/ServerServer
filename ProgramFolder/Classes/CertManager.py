from datetime import datetime, timedelta
import ipaddress
import os
import sewer.client
from sewer.crypto import AcmeKey, AcmeAccount
import sewer.dns_providers.cloudflare


class CertManager:
    def __init__(self):
        self.hostname = ""
        self.path = ""
        self.ips = []
        self.cert_file = "cert.pem"
        self.pem_file = "key.pem"

        self.account_key = "account.key"

        self.selfSigned = False

        self.cloudflare_email = ""
        self.cloudflare_api_key = ""
        self.domain = ""

    def setup(self, hostname, path, ips=None, selfSigned=False, cloudflare_email="", cloudflare_api_key="", domain=""):
        if not ips:
            self.ips = []
        self.hostname = hostname
        self.path = path
        self.selfSigned = selfSigned
        self.cloudflare_email = cloudflare_email
        self.cloudflare_api_key = cloudflare_api_key
        self.domain = domain

    def _cert_file_path(self):
        return os.path.join(self.path, self.cert_file)

    def _key_file_path(self):
        return os.path.join(self.path, self.pem_file)

    def get_cert_file_path(self):
        self.create_files_if_missing()
        return self._cert_file_path()

    def get_key_file_path(self):
        self.create_files_if_missing()
        return self._key_file_path()

    def create_files_if_missing(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        if not os.path.isfile(self._cert_file_path()) or not os.path.isfile(self._key_file_path()):
            if self.selfSigned:
                cert, pem = self.generate_selfsigned_cert()
            else:
                cert, pem = self.generate_signed_cert()
            with open(self._cert_file_path(), "wb") as f:
                f.write(cert)
            with open(self._key_file_path(), "wb") as f:
                f.write(pem)

    def generate_selfsigned_cert(self, key=None):
        """Generates self signed certificate for a hostname, and optional IP addresses."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate our key
        if key is None:
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )

        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.hostname)
        ])

        # best practice seem to be to include the hostname in the SAN, which *SHOULD* mean COMMON_NAME is ignored.
        alt_names = [x509.DNSName(self.hostname)]

        # allow addressing by IP, for when you don't have real DNS (common in most testing scenarios
        ip_addresses = self.ips
        if ip_addresses:
            for addr in ip_addresses:
                # openssl wants DNSnames for ips...
                alt_names.append(x509.DNSName(addr))
                # ... whereas golang's crypto/tls is stricter, and needs IPAddresses
                # note: older versions of cryptography do not understand ip_address objects
                alt_names.append(x509.IPAddress(ipaddress.ip_address(addr)))

        san = x509.SubjectAlternativeName(alt_names)

        # path_len=0 means this cert can only sign itself, not other certs.
        basic_contraints = x509.BasicConstraints(ca=True, path_length=0)
        now = datetime.utcnow()
        cert = (
            x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(key.public_key())
                .serial_number(1000)
                .not_valid_before(now)
                .not_valid_after(now + timedelta(days=10 * 365))
                .add_extension(basic_contraints, False)
                .add_extension(san, False)
                .sign(key, hashes.SHA256(), default_backend())
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cert_pem, key_pem

    def get_client(self, key):
        if not self.cloudflare_email or not self.cloudflare_api_key or not self.domain:
            return None
        dns_class = sewer.dns_providers.cloudflare.CloudFlareDns(
            CLOUDFLARE_EMAIL=self.cloudflare_email,
            CLOUDFLARE_API_KEY=self.cloudflare_api_key
        )
        if os.path.isfile(os.path.join(self.path, self.account_key)):
            a = AcmeAccount.read_pem(os.path.join(self.path, self.account_key))
            new_acc = False
        else:
            acc = AcmeKey.create("rsa2048")
            a = AcmeAccount(acc.pk, acc.key_desc)
            a.write_pem(os.path.join(self.path, self.account_key))
            new_acc = True
        client = sewer.client.Client(
            domain_alt_names=[self.domain],
            domain_name=f"*.{self.domain}",
            account=a,
            provider=dns_class,
            cert_key=key,
            is_new_acct=new_acc
        )
        return client

    def generate_signed_cert(self):
        if os.path.isfile(self._key_file_path()):
            k = AcmeKey.read_pem(self._key_file_path())
        else:
            k = AcmeKey.create("rsa2048")

        client = self.get_client(k)
        if not client:
            return self.generate_selfsigned_cert()
        certificate = client.get_certificate()
        return certificate.encode(), k.to_pem()
