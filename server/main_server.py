import asyncio
import ssl
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.makedirs("logs", exist_ok=True)

from server.room_manager import RoomManager
from server.client_handler import ClientHandler
from common.constants import HOST, PORT, MAX_CLIENTS, CERT_FILE, KEY_FILE, USE_SSL
from common.logger import logger

room_manager = RoomManager()
semaphore = asyncio.Semaphore(MAX_CLIENTS)

async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    async with semaphore:
        handler = ClientHandler(reader, writer, room_manager)
        await handler.handle()

async def main():
    if USE_SSL:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
        print("SSL/TLS Enabled")
    else:
        ssl_context = None
        print("SSL/TLS Disabled")

    server = await asyncio.start_server(
        handle_connection, HOST, PORT, ssl=ssl_context
    )
    addr = server.sockets[0].getsockname()
    print(f"Starting server...")
    print(f"Server running on {addr[0]}:{addr[1]}")
    logger.success(f"Server running on {addr[0]}:{addr[1]}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shut down.")