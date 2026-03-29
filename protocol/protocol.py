import time
import json
from protocol.hash import generate_hash


def create_packet(packet_type, sender, **kwargs):
    packet = {
        "type": packet_type,
        "sender": sender,
        "timestamp": time.time(),
        "seq": kwargs.get("seq", 0)
    }

    # Add optional fields
    for key, value in kwargs.items():
        packet[key] = value

    if "content" in packet:
        packet["hash"] = generate_hash(packet["content"])

    return packet


def serialize(packet: dict) -> bytes:
    return json.dumps(packet).encode("utf-8")

def deserialize(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))