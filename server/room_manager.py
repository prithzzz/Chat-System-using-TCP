import asyncio
from typing import Dict, Optional
from common.exceptions import RoomNotFoundError
from common.logger import logger
from server.message_queue import MessageQueue


class Room:
    def __init__(self, name: str):
        self.name = name
        self.members: Dict[str, asyncio.StreamWriter] = {}
        self.message_queue = MessageQueue(name)
        self.lock = asyncio.Lock()

    async def add_member(self, username: str, writer: asyncio.StreamWriter):
        async with self.lock:
            self.members[username] = writer
            logger.info(f"[{self.name}] {username} joined. Members: {list(self.members.keys())}")

    async def remove_member(self, username: str):
        async with self.lock:
            self.members.pop(username, None)
            logger.info(f"[{self.name}] {username} left.")

    async def broadcast(self, message_data: str, exclude: Optional[str] = None):
        async with self.lock:
            dead_clients = []
            for username, writer in self.members.items():
                if username == exclude:
                    continue
                try:
                    writer.write((message_data + "\n").encode())
                    await writer.drain()
                except Exception:
                    dead_clients.append(username)
            for u in dead_clients:
                self.members.pop(u, None)

    def is_empty(self) -> bool:
        return len(self.members) == 0

    def member_list(self) -> list:
        return list(self.members.keys())


class RoomManager:
    def __init__(self):
        self._rooms: Dict[str, Room] = {}
        self._lock = asyncio.Lock()
        self._rooms["general"] = Room("general")

    async def get_or_create_room(self, room_name: str) -> Room:
        async with self._lock:
            if room_name not in self._rooms:
                self._rooms[room_name] = Room(room_name)
                logger.info(f"Room created: {room_name}")
            return self._rooms[room_name]

    async def get_room(self, room_name: str) -> Room:
        async with self._lock:
            if room_name not in self._rooms:
                raise RoomNotFoundError(f"Room '{room_name}' does not exist.")
            return self._rooms[room_name]

    async def delete_room_if_empty(self, room_name: str):
        async with self._lock:
            if room_name in self._rooms and self._rooms[room_name].is_empty():
                if room_name != "general":
                    del self._rooms[room_name]
                    logger.info(f"Room deleted (empty): {room_name}")

    def list_rooms(self) -> list:
        return [
            {"name": name, "members": room.member_list()}
            for name, room in self._rooms.items()
        ]