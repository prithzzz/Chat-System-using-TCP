import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class Message:
    seq_num: int
    sender: str
    room: str
    content: str
    timestamp: float = field(default_factory=time.time)
    msg_type: str = "chat"  # chat | system | file

class MessageQueue:
    """
    Per-room message queue with sequence numbering.
    Guarantees ordering even under concurrent sends.
    """
    def __init__(self, room_name: str):
        self.room_name = room_name
        self._queue: deque = deque(maxlen=500)
        self._seq_counter = 0
        self._lock = asyncio.Lock()

    async def enqueue(self, sender: str, content: str, msg_type: str = "chat") -> Message:
        async with self._lock:
            self._seq_counter += 1
            msg = Message(
                seq_num=self._seq_counter,
                sender=sender,
                room=self.room_name,
                content=content,
                msg_type=msg_type
            )
            self._queue.append(msg)
            return msg

    def get_history(self, limit: int = 20) -> list:
        return list(self._queue)[-limit:]
