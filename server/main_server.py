import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create logs folder before logger loads
os.makedirs("logs", exist_ok=True)

from server.room_manager import RoomManager
from server.client_handler import ClientHandler
from common.constants import HOST, PORT, MAX_CLIENTS
from common.logger import logger

room_manager = RoomManager()
semaphore = asyncio.Semaphore(MAX_CLIENTS)

async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    async with semaphore:
        handler = ClientHandler(reader, writer, room_manager)
        await handler.handle()

async def main():
    server = await asyncio.start_server(handle_connection, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"Server running on {addr[0]}:{addr[1]}")
    logger.success(f"Server running on {addr[0]}:{addr[1]}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    print(" Starting server...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shut down.")