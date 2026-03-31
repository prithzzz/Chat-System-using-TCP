import asyncio
import json
import os
import hashlib
import base64

CHUNK_SIZE = 1024  # 1KB per chunk

# ─── SEND FILE ────────────────────────────────────────
async def send_file(writer, filepath: str, room: str):
    """Send a file in chunks to the server."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return False

    filename  = os.path.basename(filepath)
    filesize  = os.path.getsize(filepath)

    # Calculate file hash for integrity check
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    total_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE

    print(f"[*] Sending file: {filename} ({filesize} bytes, {total_chunks} chunks)")

    # Step 1: Send FILE_META packet
    meta_packet = json.dumps({
        "type":         "file_meta",
        "filename":     filename,
        "filesize":     filesize,
        "total_chunks": total_chunks,
        "hash":         file_hash,
        "room":         room
    }) + "\n"
    writer.write(meta_packet.encode())
    await writer.drain()

    # Step 2: Send FILE_CHUNK packets
    chunk_num = 0
    with open(filepath, "rb") as f:
        while True:
            chunk_data = f.read(CHUNK_SIZE)
            if not chunk_data:
                break
            chunk_num += 1
            encoded = base64.b64encode(chunk_data).decode("utf-8")
            chunk_packet = json.dumps({
                "type":      "file_chunk",
                "filename":  filename,
                "chunk_num": chunk_num,
                "data":      encoded
            }) + "\n"
            writer.write(chunk_packet.encode())
            await writer.drain()

            # Show progress
            progress = int((chunk_num / total_chunks) * 100)
            print(f"\r[*] Uploading: {progress}% ({chunk_num}/{total_chunks})", end="", flush=True)

    # Step 3: Send FILE_END packet
    end_packet = json.dumps({
        "type":     "file_end",
        "filename": filename,
        "hash":     file_hash
    }) + "\n"
    writer.write(end_packet.encode())
    await writer.drain()

    print(f"\n[✓] File sent: {filename}")
    return True


# ─── RECEIVE FILE ─────────────────────────────────────
class FileReceiver:
    """Handles receiving file chunks and reassembling."""
    def __init__(self):
        self.pending_files = {}  # filename → {meta, chunks}

    def handle_meta(self, data: dict):
        filename     = data.get("filename")
        total_chunks = data.get("total_chunks")
        file_hash    = data.get("hash")
        sender       = data.get("sender", "unknown")

        self.pending_files[filename] = {
            "total_chunks": total_chunks,
            "hash":         file_hash,
            "sender":       sender,
            "chunks":       {},
            "received":     0
        }
        print(f"\n[*] Incoming file: {filename} from {sender} ({total_chunks} chunks)")

    def handle_chunk(self, data: dict):
        filename  = data.get("filename")
        chunk_num = data.get("chunk_num")
        chunk_data = base64.b64decode(data.get("data", ""))

        if filename not in self.pending_files:
            return

        self.pending_files[filename]["chunks"][chunk_num] = chunk_data
        self.pending_files[filename]["received"] += 1

        received      = self.pending_files[filename]["received"]
        total_chunks  = self.pending_files[filename]["total_chunks"]
        progress      = int((received / total_chunks) * 100)
        print(f"\r[*] Downloading: {progress}% ({received}/{total_chunks})", end="", flush=True)

    def handle_end(self, data: dict) -> bool:
        filename  = data.get("filename")
        file_hash = data.get("hash")

        if filename not in self.pending_files:
            return False

        file_info = self.pending_files[filename]
        chunks    = file_info["chunks"]
        total     = file_info["total_chunks"]

        # Reassemble file in order
        os.makedirs("received_files", exist_ok=True)
        save_path = os.path.join("received_files", filename)

        with open(save_path, "wb") as f:
            for i in range(1, total + 1):
                if i in chunks:
                    f.write(chunks[i])
                else:
                    print(f"\n[ERROR] Missing chunk {i} for {filename}")
                    return False

        # Verify hash
        sha256 = hashlib.sha256()
        with open(save_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024), b""):
                sha256.update(chunk)
        actual_hash = sha256.hexdigest()

        if actual_hash == file_hash:
            print(f"\n[✓] File received and verified: {save_path}")
            del self.pending_files[filename]
            return True
        else:
            print(f"\n[ERROR] File hash mismatch! File may be corrupted.")
            os.remove(save_path)
            return False
