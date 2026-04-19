import re
import socket
import uuid
from typing import Any


def _build_probe_message(message_id: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{message_id}</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>"""


def discover_onvif_devices(timeout_seconds: float = 2.0) -> list[dict[str, Any]]:
    timeout_seconds = max(0.5, min(10.0, timeout_seconds))
    message = _build_probe_message(str(uuid.uuid4())).encode("utf-8")
    devices: dict[str, dict[str, Any]] = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(timeout_seconds)
        sock.sendto(message, ("239.255.255.250", 3702))

        while True:
            try:
                payload, addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            text = payload.decode("utf-8", errors="ignore")
            xaddrs = re.findall(r"<(?:\w+:)?XAddrs>(.*?)</(?:\w+:)?XAddrs>", text, flags=re.IGNORECASE | re.DOTALL)
            scopes = re.findall(r"<(?:\w+:)?Scopes>(.*?)</(?:\w+:)?Scopes>", text, flags=re.IGNORECASE | re.DOTALL)
            addresses = []
            for blob in xaddrs:
                addresses.extend(part.strip() for part in blob.split() if part.strip())
            key = f"{addr[0]}:{addr[1]}"
            devices[key] = {
                "ip": addr[0],
                "port": addr[1],
                "xaddrs": addresses,
                "scopes": scopes[0].strip() if scopes else "",
            }
    finally:
        sock.close()
    return list(devices.values())
