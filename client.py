import asyncio
import json
import sys
import os
import ssl
import base64
import hashlib

# ─── CONFIG ───────────────────────────────────────────
HOST = os.getenv("CHAT_SERVER_IP", "127.0.0.1") #server IP
PORT = 9999
CHUNK_SIZE = 1024

# ─── COLORS FOR TERMINAL ──────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    print(f"{CYAN}{BOLD}")
    print("╔══════════════════════════════════════╗")
    print("║       MULTIROOM CHAT SYSTEM          ║")
    print("║      Client v2.0  (SSL + Files)      ║")
    print("╚══════════════════════════════════════╝")
    print(f"{RESET}")

def print_help():
    print(f"{YELLOW}")
    print("─── COMMANDS ───────────────────────────")
    print("  /switch <room>      → Switch to another room")
    print("  /rooms              → List all available rooms")
    print("  /pm <user> <msg>    → Send private message")
    print("  /sendfile <path>    → Send a file to room")
    print("  /quit               → Disconnect and exit")
    print("  /help               → Show this help")
    print("────────────────────────────────────────")
    print(f"{RESET}")

# ─── FILE RECEIVER ────────────────────────────────────
class FileReceiver:
    def __init__(self):
        self.pending = {}

    def handle_meta(self, data):
        filename = data.get("filename")
        self.pending[filename] = {
            "total":    data.get("total_chunks"),
            "hash":     data.get("hash"),
            "sender":   data.get("sender", "?"),
            "chunks":   {},
            "received": 0
        }
        print(f"\n{YELLOW}[FILE] Incoming: {filename} from {data.get('sender','?')}{RESET}")

    def handle_chunk(self, data):
        filename   = data.get("filename")
        chunk_num  = data.get("chunk_num")
        chunk_data = base64.b64decode(data.get("data", ""))
        if filename not in self.pending:
            return
        self.pending[filename]["chunks"][chunk_num] = chunk_data
        self.pending[filename]["received"] += 1
        received = self.pending[filename]["received"]
        total    = self.pending[filename]["total"]
        pct      = int((received / total) * 100)
        print(f"\r{YELLOW}[FILE] Downloading: {pct}% ({received}/{total}){RESET}", end="", flush=True)

    def handle_end(self, data):
        filename  = data.get("filename")
        file_hash = data.get("hash")
        if filename not in self.pending:
            return
        info   = self.pending[filename]
        chunks = info["chunks"]
        total  = info["total"]
        os.makedirs("received_files", exist_ok=True)
        save_path = os.path.join("received_files", filename)
        with open(save_path, "wb") as f:
            for i in range(1, total + 1):
                if i in chunks:
                    f.write(chunks[i])
        sha256 = hashlib.sha256()
        with open(save_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024), b""):
                sha256.update(chunk)
        if sha256.hexdigest() == file_hash:
            print(f"\n{GREEN}[✓] File saved: {save_path}{RESET}")
        else:
            print(f"\n{RED}[!] File corrupted — hash mismatch!{RESET}")
            os.remove(save_path)
        del self.pending[filename]

file_receiver = FileReceiver()

# ─── SEND FILE ────────────────────────────────────────
async def send_file(writer, filepath: str, room: str):
    if not os.path.exists(filepath):
        print(f"{RED}[!] File not found: {filepath}{RESET}")
        return
    filename     = os.path.basename(filepath)
    filesize     = os.path.getsize(filepath)
    total_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE

    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    print(f"{YELLOW}[FILE] Sending: {filename} ({filesize} bytes){RESET}")

    writer.write((json.dumps({
        "type": "file_meta", "filename": filename,
        "filesize": filesize, "total_chunks": total_chunks,
        "hash": file_hash, "room": room
    }) + "\n").encode())
    await writer.drain()

    chunk_num = 0
    with open(filepath, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            chunk_num += 1
            writer.write((json.dumps({
                "type": "file_chunk", "filename": filename,
                "chunk_num": chunk_num,
                "data": base64.b64encode(data).decode()
            }) + "\n").encode())
            await writer.drain()
            pct = int((chunk_num / total_chunks) * 100)
            print(f"\r{YELLOW}[FILE] Uploading: {pct}%{RESET}", end="", flush=True)

    writer.write((json.dumps({
        "type": "file_end", "filename": filename, "hash": file_hash
    }) + "\n").encode())
    await writer.drain()
    print(f"\n{GREEN}[✓] File sent: {filename}{RESET}")

# ─── RECEIVE MESSAGES ─────────────────────────────────
async def receive_messages(reader, username):
    while True:
        try:
            line = await reader.readline()
            if not line:
                print(f"\n{RED}[!] Disconnected from server.{RESET}")
                break

            data     = json.loads(line.decode().strip())
            msg_type = data.get("type")

            if msg_type == "chat":
                sender  = data.get("sender", "?")
                content = data.get("content", "")
                room    = data.get("room", "")
                if sender == username:
                    print(f"\r{GREEN}[You → #{room}] {content}{RESET}")
                else:
                    print(f"\r{CYAN}[{sender} → #{room}] {content}{RESET}")

            elif msg_type == "private":
                print(f"\r{YELLOW}[PM from {data.get('from','?')}] {data.get('content','')}{RESET}")

            elif msg_type == "private_sent":
                print(f"\r{YELLOW}[PM to {data.get('to','?')}] {data.get('content','')}{RESET}")

            elif msg_type == "system":
                print(f"\r{YELLOW}[*] {data.get('content','')}{RESET}")

            elif msg_type == "joined":
                members = data.get("members", [])
                print(f"\r{GREEN}[✓] Joined room: #{data.get('room','')}{RESET}")
                print(f"{WHITE}    Members: {', '.join(members)}{RESET}")

            elif msg_type == "history":
                messages = data.get("messages", [])
                if messages:
                    print(f"\r{YELLOW}── History for #{data.get('room','')} ──{RESET}")
                    for m in messages:
                        print(f"  {CYAN}[{m['sender']}]{RESET} {m['content']}")
                    print(f"{YELLOW}── End of history ──{RESET}")

            elif msg_type == "rooms":
                print(f"\r{YELLOW}── Available Rooms ──{RESET}")
                for r in data.get("rooms", []):
                    print(f"  #{r.get('name')} ({len(r.get('members',[]))} members): {', '.join(r.get('members',[]))}")
                print(f"{YELLOW}─────────────────────{RESET}")

            elif msg_type == "file_meta":
                file_receiver.handle_meta(data)

            elif msg_type == "file_chunk":
                file_receiver.handle_chunk(data)

            elif msg_type == "file_end":
                file_receiver.handle_end(data)

            elif msg_type == "error":
                print(f"\r{RED}[ERROR] {data.get('content','')}{RESET}")

            elif msg_type in ("pong", "info"):
                pass

            print(f"{WHITE}> {RESET}", end="", flush=True)

        except json.JSONDecodeError:
            pass
        except asyncio.IncompleteReadError:
            print(f"\n{RED}[!] Connection lost.{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[!] Receive error: {e}{RESET}")
            break

# ─── SEND MESSAGES ────────────────────────────────────
async def send_messages(writer, current_room):
    loop = asyncio.get_event_loop()
    room = [current_room]

    while True:
        try:
            print(f"{WHITE}> {RESET}", end="", flush=True)
            line = await loop.run_in_executor(None, sys.stdin.readline)
            line = line.strip()
            if not line:
                continue

            if line.startswith("/quit"):
                print(f"{RED}[*] Disconnecting...{RESET}")
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
                return

            elif line.startswith("/switch "):
                new_room = line.split(" ", 1)[1].strip()
                room[0]  = new_room
                writer.write((json.dumps({"type": "switch_room", "room": new_room}) + "\n").encode())
                await writer.drain()

            elif line.startswith("/rooms"):
                writer.write((json.dumps({"type": "list_rooms"}) + "\n").encode())
                await writer.drain()

            elif line.startswith("/pm "):
                parts = line.split(" ", 2)
                if len(parts) < 3:
                    print(f"{RED}Usage: /pm <username> <message>{RESET}")
                    continue
                writer.write((json.dumps({
                    "type": "private",
                    "to": parts[1].strip(),
                    "content": parts[2].strip()
                }) + "\n").encode())
                await writer.drain()

            elif line.startswith("/sendfile "):
                filepath = line.split(" ", 1)[1].strip()
                await send_file(writer, filepath, room[0])

            elif line.startswith("/help"):
                print_help()

            elif line.startswith("/ping"):
                writer.write((json.dumps({"type": "ping"}) + "\n").encode())
                await writer.drain()

            else:
                writer.write((json.dumps({"type": "chat", "content": line}) + "\n").encode())
                await writer.drain()

        except (EOFError, KeyboardInterrupt):
            print(f"\n{RED}[*] Exiting...{RESET}")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            return
        except Exception as e:
            print(f"{RED}[!] Send error: {e}{RESET}")
            break

# ─── MAIN ─────────────────────────────────────────────
async def main():
    clear()
    print_banner()

    username = input(f"{WHITE}Enter your name : {RESET}").strip()
    if not username:
        print(f"{RED}Username cannot be empty!{RESET}")
        return

    room = input(f"{WHITE}Enter room name  : {RESET}").strip()
    if not room:
        room = "general"

    print(f"\n{YELLOW}[*] Connecting to {HOST}:{PORT}...{RESET}")
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode    = ssl.CERT_NONE
        reader, writer = await asyncio.open_connection(HOST, PORT, ssl=ssl_context)
    except ConnectionRefusedError:
        print(f"{RED}[!] Cannot connect — make sure server is running!{RESET}")
        return
    except Exception as e:
        print(f"{RED}[!] Connection error: {e}{RESET}")
        return

    print(f"{GREEN}[✓] Connected! (SSL secured 🔐){RESET}")
    await reader.readline()

    writer.write((json.dumps({
        "type": "join", "username": username, "room": room
    }) + "\n").encode())
    await writer.drain()

    print_help()
    print(f"{GREEN}[✓] Joining room: #{room} as {username}{RESET}\n")

    try:
        await asyncio.gather(
            receive_messages(reader, username),
            send_messages(writer, room)
        )
    except Exception:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    print(f"\033[91m[*] Client shut down.\033[0m")