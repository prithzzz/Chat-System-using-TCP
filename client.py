import asyncio
import json
import sys
import os
import ssl

# CONFIG 
PORT = 9999
HOST = os.getenv("CHAT_SERVER_IP", "127.0.0.1") #server IP

# COLORS FOR TERMINAL
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
    print("║             Client                   ║")
    print("╚══════════════════════════════════════╝")
    print(f"{RESET}")

def print_help():
    print(f"{YELLOW}")
    print("─── COMMANDS ───────────────────────────")
    print("  /switch <room>   → Switch to another room")
    print("  /rooms           → List all available rooms")
    print("  /pm <user> <msg> → Send private message")
    print("  /quit            → Disconnect and exit")
    print("  /help            → Show this help")
    print("────────────────────────────────────────")
    print(f"{RESET}")

# RECEIVE MESSAGES FROM SERVER
async def receive_messages(reader, username):
    """Continuously listen for messages from server."""
    while True:
        try:
            line = await reader.readline()
            if not line:
                print(f"\n{RED}[!] Disconnected from server.{RESET}")
                break

            data = json.loads(line.decode().strip())
            msg_type = data.get("type")

            if msg_type == "chat":
                sender  = data.get("sender", "?")
                content = data.get("content", "")
                room    = data.get("room", "")
                seq     = data.get("seq", "")
                if sender == username:
                    print(f"\r{GREEN}[You → #{room}] {content}{RESET}")
                else:
                    print(f"\r{CYAN}[{sender} → #{room}] {content}{RESET}")

            elif msg_type == "private":
                frm     = data.get("from", "?")
                content = data.get("content", "")
                print(f"\r{YELLOW}[PM from {frm}] {content}{RESET}")

            elif msg_type == "private_sent":
                to      = data.get("to", "?")
                content = data.get("content", "")
                print(f"\r{YELLOW}[PM to {to}] {content}{RESET}")

            elif msg_type == "system":
                content = data.get("content", "")
                print(f"\r{YELLOW}[*] {content}{RESET}")

            elif msg_type == "joined":
                room    = data.get("room", "")
                members = data.get("members", [])
                print(f"\r{GREEN}[✓] Joined room: #{room}{RESET}")
                print(f"{WHITE}    Members: {', '.join(members)}{RESET}")

            elif msg_type == "history":
                room     = data.get("room", "")
                messages = data.get("messages", [])
                if messages:
                    print(f"\r{YELLOW}── History for #{room} ──{RESET}")
                    for m in messages:
                        print(f"  {CYAN}[{m['sender']}]{RESET} {m['content']}")
                    print(f"{YELLOW}── End of history ──{RESET}")

            elif msg_type == "rooms":
                rooms = data.get("rooms", [])
                print(f"\r{YELLOW}── Available Rooms ──{RESET}")
                for r in rooms:
                    members = r.get("members", [])
                    name    = r.get("name", "")
                    print(f"  #{name} ({len(members)} members): {', '.join(members)}")
                print(f"{YELLOW}─────────────────────{RESET}")

            elif msg_type == "error":
                content = data.get("content", "")
                print(f"\r{RED}[ERROR] {content}{RESET}")

            elif msg_type == "pong":
                pass

            elif msg_type == "info":
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

# SEND MESSAGES TO SERVER
async def send_messages(writer):
    """Read user input and send to server."""
    loop = asyncio.get_event_loop()

    while True:
        try:
            print(f"{WHITE}> {RESET}", end="", flush=True)

            line = await loop.run_in_executor(None, sys.stdin.readline)
            line = line.strip()

            if not line:
                continue

            # COMMANDS
            if line.startswith("/quit"):
                print(f"{RED}[*] Disconnecting...{RESET}")
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
                return                           

            elif line.startswith("/switch "):
                room_input = line.split(" ", 1)[1].strip()

                if not room_input:
                    print(f"{RED}Usage: /switch <room name or number>{RESET}")
                    continue

                room = room_input

                packet = json.dumps({
                    "type": "switch_room",
                    "room": room
                }) + "\n"

                writer.write(packet.encode())
                await writer.drain()

            elif line.startswith("/rooms"):
                packet = json.dumps({"type": "list_rooms"}) + "\n"
                writer.write(packet.encode())
                await writer.drain()

            elif line.startswith("/pm "):
                parts = line.split(" ", 2)
                if len(parts) < 3:
                    print(f"{RED}Usage: /pm <username> <message>{RESET}")
                    continue
                to_user = parts[1].strip()
                content = parts[2].strip()
                packet  = json.dumps({
                    "type":    "private",
                    "to":      to_user,
                    "content": content
                }) + "\n"
                writer.write(packet.encode())
                await writer.drain()

            elif line.startswith("/gm"):   # normal message (not a command)
                packet = json.dumps({
                    "type": "chat",
                    "content": line
                }) + "\n"

                writer.write(packet.encode())
                await writer.drain()                

            elif line.startswith("/help"):
                print_help()

            elif line.startswith("/ping"):
                packet = json.dumps({"type": "ping"}) + "\n"
                writer.write(packet.encode())
                await writer.drain()

            else:
                # Normal chat message
                packet = json.dumps({
                    "type":    "chat",
                    "content": line
                }) + "\n"
                writer.write(packet.encode())
                await writer.drain()

        except (EOFError, KeyboardInterrupt):
            print(f"\n{RED}[*] Exiting...{RESET}")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            return                               # ← CLEAN EXIT
        except Exception as e:
            print(f"{RED}[!] Send error: {e}{RESET}")
            break

# ─── MAIN ───
async def main():
    clear()
    print_banner()

    # Get username and room
    username = input(f"{WHITE}Enter your name : {RESET}").strip()
    if not username:
        print(f"{RED}Username cannot be empty!{RESET}")
        return

    room_input = input(f"{WHITE}Enter room name or number : {RESET}").strip()
    if not room_input:
        room = "general"
    else:
        room = room_input  # works for BOTH name and number

    # Connect to server with SSL
    print(f"\n{YELLOW}[*] Connecting to {HOST}:{PORT}...{RESET}")
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.open_connection(
            HOST, PORT, ssl=ssl_context
        )
    except ConnectionRefusedError:
        print(f"{RED}[!] Cannot connect to server at {HOST}:{PORT}")
        print(f"    Make sure the server is running first!{RESET}")
        return
    except Exception as e:
        print(f"{RED}[!] Connection error: {e}{RESET}")
        return

    print(f"{GREEN}[✓] Connected to server! (SSL secured 🔐){RESET}")

    # Wait for server's "Enter username" prompt
    await reader.readline()

    # Send JOIN packet
    join_packet = json.dumps({
        "type":     "join",
        "username": username,
        "room":     room
    }) + "\n"
    writer.write(join_packet.encode())
    await writer.drain()

    print_help()
    print(f"{GREEN}[✓] Joining room: #{room} as {username}{RESET}\n")

    # Run receiver and sender concurrently
    try:
        await asyncio.gather(
            receive_messages(reader, username),
            send_messages(writer)
        )
    except Exception:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    print(f"\033[91m[*] Client shut down.\033[0m")