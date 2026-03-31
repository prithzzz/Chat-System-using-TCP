import asyncio
import json
from server.room_manager import RoomManager
from common.logger import logger
from common.exceptions import RoomNotFoundError

class ClientHandler:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, room_manager: RoomManager):
        self.reader = reader
        self.writer = writer
        self.room_manager = room_manager
        self.username: str = ""
        self.current_room: str = ""
        self.addr = writer.get_extra_info("peername")

    async def send(self, data: dict):
        """Send a JSON message to this client."""
        try:
            msg = json.dumps(data) + "\n"
            self.writer.write(msg.encode())
            await self.writer.drain()
        except Exception as e:
            logger.warning(f"Send failed to {self.username}: {e}")

    async def handle(self):
        """Main loop: read and process messages from this client."""
        logger.info(f"New connection from {self.addr}")
        try:
            await self._register()

            while True:
                line = await self.reader.readline()
                if not line:
                    break
                await self._process_message(line.decode().strip())

        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            logger.error(f"Error with {self.username}: {e}")
        finally:
            await self._disconnect()

    async def _register(self):
        await self.send({"type": "info", "content": "Enter username:"})
        while True:
            line = await self.reader.readline()
            if not line:
                raise ConnectionError("Client disconnected before registering")

            data = json.loads(line.decode().strip())
            if data.get("type") == "join":
                self.username = data.get("username", "").strip()
                room_name = data.get("room", "general")

                if not self.username:
                    await self.send({"type": "error", "content": "Username cannot be empty."})
                    continue

                await self._join_room(room_name)
                break

    async def _join_room(self, room_name: str):
        if self.current_room:
            try:
                old_room = await self.room_manager.get_room(self.current_room)
                await old_room.remove_member(self.username)
                await old_room.broadcast(
                    json.dumps({
                        "type": "system",
                        "content": f"{self.username} left the room.",
                        "room": self.current_room,
                    })
                )
                await self.room_manager.delete_room_if_empty(self.current_room)
            except RoomNotFoundError:
                pass

        room = await self.room_manager.get_or_create_room(room_name)
        await room.add_member(self.username, self.writer)
        self.current_room = room_name

        history = room.message_queue.get_history(limit=20)
        await self.send({
            "type": "history",
            "room": room_name,
            "messages": [
                {
                    "seq": m.seq_num,
                    "sender": m.sender,
                    "content": m.content,
                    "time": m.timestamp,
                }
                for m in history
            ],
        })

        await room.broadcast(
            json.dumps({
                "type": "system",
                "content": f"{self.username} joined the room.",
                "room": room_name,
            }),
            exclude=self.username,
        )

        await self.send({
            "type": "joined",
            "room": room_name,
            "members": room.member_list(),
        })

    async def _process_message(self, raw: str):
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self.send({"type": "error", "content": "Invalid JSON."})
            return

        msg_type = data.get("type")

        if msg_type == "chat":
            await self._handle_chat(data)
        elif msg_type == "switch_room":
            await self._join_room(data.get("room", "general"))
        elif msg_type == "list_rooms":
            await self.send({"type": "rooms", "rooms": self.room_manager.list_rooms()})
        elif msg_type == "private":
            await self._handle_private(data)
        elif msg_type == "ping":
            await self.send({"type": "pong"})
        elif msg_type in ("file_meta", "file_chunk", "file_end"):
            await self._handle_file(data)
        else:
            await self.send({"type": "error", "content": f"Unknown message type: {msg_type}"})

    async def _handle_chat(self, data: dict):
        if not self.current_room:
            await self.send({"type": "error", "content": "You are not in a room."})
            return

        content = data.get("content", "").strip()
        if not content:
            return

        try:
            room = await self.room_manager.get_room(self.current_room)
            msg = await room.message_queue.enqueue(self.username, content)
            await room.broadcast(
                json.dumps({
                    "type": "chat",
                    "seq": msg.seq_num,
                    "sender": self.username,
                    "content": content,
                    "room": self.current_room,
                    "time": msg.timestamp,
                })
            )
        except RoomNotFoundError:
            await self.send({"type": "error", "content": "Room not found."})

    async def _handle_private(self, data: dict):
        target = data.get("to", "")
        content = data.get("content", "")

        if not self.current_room:
            return

        try:
            room = await self.room_manager.get_room(self.current_room)
            async with room.lock:
                if target not in room.members:
                    await self.send({
                        "type": "error",
                        "content": f"User '{target}' not found in room.",
                    })
                    return
                target_writer = room.members[target]

            msg_data = json.dumps({
                "type": "private",
                "from": self.username,
                "to": target,
                "content": content,
            }) + "\n"

            target_writer.write(msg_data.encode())
            await target_writer.drain()

            await self.send({
                "type": "private_sent",
                "to": target,
                "content": content,
            })
        except RoomNotFoundError:
            pass

    async def _handle_file(self, data: dict):
        """Handle file packets and broadcast to everyone in room except sender."""
        if not self.current_room:
            await self.send({"type": "error", "content": "You are not in a room."})
            return

        try:
            room = await self.room_manager.get_room(self.current_room)

            if data.get("type") == "file_meta":
                data["sender"] = self.username
                data["room"] = self.current_room

            await room.broadcast(json.dumps(data), exclude=self.username)

        except RoomNotFoundError:
            await self.send({"type": "error", "content": "Room not found."})

    async def _disconnect(self):
        logger.info(f"{self.username} disconnected from {self.addr}")

        if self.current_room:
            try:
                room = await self.room_manager.get_room(self.current_room)
                await room.remove_member(self.username)
                await room.broadcast(
                    json.dumps({
                        "type": "system",
                        "content": f"{self.username} disconnected.",
                        "room": self.current_room,
                    })
                )
                await self.room_manager.delete_room_if_empty(self.current_room)
            except Exception:
                pass

        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
