from protocol.protocol import create_packet, serialize, deserialize
from network.socket_manager import send_packet, receive_packet
from network.utils import validate_packet

def perform_handshake(sock, username):
    """Client sends JOIN packet initially"""
    packet = create_packet("JOIN", sender=username)
    send_packet(sock, serialize(packet))


def receive_handshake(sock):
    """Server receives JOIN packet"""
    data = receive_packet(sock)
    if not data:
        return None

    packet = deserialize(data)
    if not validate_packet(packet):
        return None
    
    return packet.get("sender")