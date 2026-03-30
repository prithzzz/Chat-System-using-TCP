# MULTI-ROOM SECURE CHAT SYSTEM WITH FILE TRANSFER

This project implements a multi-room secure chat system that supports:

- Multiple chat rooms  
- Private messaging  
- File transfer (upload/download)  
- Smooth user experience for clients  

The system is built using Python and follows a modular architecture.

--------------------------------------------------

## TEAM MEMBERS & RESPONSIBILITIES

### Prithika — Networking + Protocol Layer
- Handles TCP socket communication  
- Packet framing & serialization  
- Client connection handshake  
- Room join/leave packets  
- File metadata transfer packets  

### Nikhil — Server + Concurrency Engine
- Handles multiple clients simultaneously  
- Multi-room logic  
- Ensures message ordering per room  
- Fault tolerance (disconnects, crashes)  
- Broadcast system & room management  

### Priyanka — Client + File Transfer + UX
- Main file: python.py  
- Chat interface (CLI)  
- Room switching & messaging  
- File transfer (upload/download)  
- Smooth user experience  

--------------------------------------------------

## PROJECT STRUCTURE

Chat-System-using-TCP/

backend/ → Server logic  
protocol/ → Protocol definitions  
common/ → Shared utilities  
docs/ → Documentation  
logs/ → Logs  
tests/ → Testing  
python.py → Client (Priyanka)  
README.md → Documentation  

--------------------------------------------------

## HOW TO RUN

Start Server:
python server/main_server.py  

Start Client:
python client.py  

Enter your name and room to begin chatting.

--------------------------------------------------

## FILE TRANSFER

Send file using:
/send filename.ext  

Received files will be saved as:
received_filename.ext  

--------------------------------------------------

## REQUIREMENTS

Python 3.14+  
socket, threading, os  

--------------------------------------------------

DEMO NOTES

- Run server first  
- Use same WiFi for testing  
- Test multiple users  
- Show chat and file transfer  
