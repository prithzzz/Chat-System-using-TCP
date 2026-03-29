from protocol.hash import verify_hash

def validate_packet(packet: dict):
    required_fields = ["type", "sender", "timestamp"]

    for field in required_fields:
        if field not in packet:
            return False
    return True


def create_error(message):
    return {
        "type": "ERROR",
        "message": message
    }


def verify_packet_integrity(packet):
    if "content" in packet and "hash" in packet:
        return verify_hash(packet["content"], packet["hash"])
    return True