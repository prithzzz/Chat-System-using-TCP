import asyncio
import json
import ssl
import time

HOST = "127.0.0.1"
PORT = 9999
RESULTS = []

async def test_client(client_id: int, num_messages: int = 5):
    """Single test client that connects, sends messages and disconnects."""
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        start = time.time()
        reader, writer = await asyncio.open_connection(HOST, PORT, ssl=ssl_context)

        # Wait for info prompt
        await reader.readline()

        # Join room
        join = json.dumps({
            "type": "join",
            "username": f"testuser_{client_id}",
            "room": "general"
        }) + "\n"
        writer.write(join.encode())
        await writer.drain()

        # Read history response
        await reader.readline()
        await reader.readline()

        # Send messages
        for i in range(num_messages):
            msg = json.dumps({
                "type": "chat",
                "content": f"Test message {i} from client {client_id}"
            }) + "\n"
            writer.write(msg.encode())
            await writer.drain()

        connect_time = time.time() - start
        RESULTS.append({
            "client_id": client_id,
            "connect_time": round(connect_time, 3),
            "status": "success"
        })

        writer.close()
        await writer.wait_closed()

    except Exception as e:
        RESULTS.append({
            "client_id": client_id,
            "connect_time": -1,
            "status": f"failed: {e}"
        })

async def run_test(num_clients: int, num_messages: int = 5):
    """Run performance test with given number of clients."""
    print(f"\n{'='*50}")
    print(f"Testing with {num_clients} clients, {num_messages} messages each")
    print(f"{'='*50}")

    RESULTS.clear()
    start = time.time()

    # Launch all clients simultaneously
    tasks = [test_client(i, num_messages) for i in range(num_clients)]
    await asyncio.gather(*tasks, return_exceptions=True)

    total_time    = time.time() - start
    success_count = sum(1 for r in RESULTS if r["status"] == "success")
    failed_count  = num_clients - success_count
    avg_time      = sum(r["connect_time"] for r in RESULTS if r["connect_time"] > 0)
    avg_time      = round(avg_time / max(success_count, 1), 3)
    total_msgs    = success_count * num_messages

    print(f"  Total clients  : {num_clients}")
    print(f"  Successful     : {success_count}")
    print(f"  Failed         : {failed_count}")
    print(f"  Total time     : {round(total_time, 3)}s")
    print(f"  Avg conn time  : {avg_time}s")
    print(f"  Total messages : {total_msgs}")
    print(f"  Msgs/second    : {round(total_msgs / max(total_time, 0.001))}")

    return {
        "clients":    num_clients,
        "success":    success_count,
        "failed":     failed_count,
        "total_time": round(total_time, 3),
        "avg_time":   avg_time,
        "msgs_per_sec": round(total_msgs / max(total_time, 0.001))
    }

async def main():
    print("╔══════════════════════════════════════╗")
    print("║   PERFORMANCE EVALUATION TEST        ║")
    print("║   Multi-Room Chat System             ║")
    print("╚══════════════════════════════════════╝")
    print(f"\nServer: {HOST}:{PORT}")
    print("Make sure server is running first!\n")

    all_results = []

    # Test with increasing number of clients
    for num_clients in [1, 5, 10, 20, 50]:
        result = await run_test(num_clients, num_messages=5)
        all_results.append(result)
        await asyncio.sleep(1)  # pause between tests

    # Final summary table
    print(f"\n{'='*60}")
    print(f"{'PERFORMANCE SUMMARY':^60}")
    print(f"{'='*60}")
    print(f"{'Clients':<12}{'Success':<12}{'Failed':<12}{'Msgs/sec':<12}{'Avg Time'}")
    print(f"{'-'*60}")
    for r in all_results:
        print(f"{r['clients']:<12}{r['success']:<12}{r['failed']:<12}{r['msgs_per_sec']:<12}{r['avg_time']}s")
    print(f"{'='*60}")
    print("\n[✓] Performance evaluation complete!")

if __name__ == "__main__":
    asyncio.run(main())
