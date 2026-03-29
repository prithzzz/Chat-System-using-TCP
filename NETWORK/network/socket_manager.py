import struct

def send_packet(sock, data: bytes):
    """Sends data with length prefix"""
    length = len(data)
    sock.sendall(struct.pack("!I", length))  # 4-byte length
    sock.sendall(data)


def receive_packet(sock):
    """Receives a full packet"""
    raw_len = recvall(sock, 4)
    if not raw_len:
        return None

    length = struct.unpack("!I", raw_len)[0]
    return recvall(sock, length)


def recvall(sock, n):
    """Ensures receiving exactly n bytes"""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data