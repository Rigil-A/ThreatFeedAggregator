# models/ioc.py

from dataclasses import dataclass
from typing import Optional, Dict
import ipaddress
import re

IP_REGEX = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
DOMAIN_REGEX = r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b"
URL_REGEX = r"https?://[^\s'\"]+"
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
HASH_REGEX = r"\b[a-fA-F0-9]{32,64}\b"


# ========================================================
# 1. IOC TYPE DETECTOR
# ========================================================

def detect_ioc_type(value: str) -> str:
    if re.fullmatch(IP_REGEX, value):
        return "ip"
    if value.startswith("http://") or value.startswith("https://"):
        return "url"
    if re.fullmatch(DOMAIN_REGEX, value):
        return "domain"
    if "@" in value and re.fullmatch(EMAIL_REGEX, value):
        return "email"
    if re.fullmatch(HASH_REGEX, value):
        return "hash"
    return "unknown"


# ========================================================
# 2. Helper check private/invalid
# ========================================================

def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except:
        return False


def is_valid_domain(domain: str) -> bool:
    return bool(re.fullmatch(DOMAIN_REGEX, domain))


# ========================================================
# 3. IOC Dataclass
# ========================================================

@dataclass
class IOC:
    value: str
    ioc_type: str
    source: Optional[str] = None
    feed_name: Optional[str] = None
    metadata: Dict = None

    def to_dict(self):
        return {
            "ioc": self.value,
            "type": self.ioc_type,
            "source": self.source,
            "feed_name": self.feed_name,
            "metadata": self.metadata or {},
        }
