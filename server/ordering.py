from typing import List
from server.message_queue import Message

def verify_ordering(messages: List[Message]) -> bool:
    """Check that a list of messages is in correct seq_num order."""
    for i in range(1, len(messages)):
        if messages[i].seq_num <= messages[i - 1].seq_num:
            return False
    return True

def find_missing_sequences(messages: List[Message]) -> List[int]:
    """Find any gaps in sequence numbers (useful for debugging)."""
    if not messages:
        return []
    expected = set(range(messages[0].seq_num, messages[-1].seq_num + 1))
    actual = set(m.seq_num for m in messages)
    return sorted(expected - actual)