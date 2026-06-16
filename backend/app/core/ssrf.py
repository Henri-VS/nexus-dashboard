import ipaddress
from urllib.parse import urlparse


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            if host in ("localhost", "metadata.google.internal") or \
               host.endswith(".local") or host.endswith(".internal"):
                return False
        return True
    except Exception:
        return False
