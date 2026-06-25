import asyncio, json, websockets

async def run():
    uri = "ws://localhost:8080/ws/execute"
    async with websockets.connect(uri) as ws:
        # Send the code that waits for input
        await ws.send(json.dumps({
            "source_code": "name = input('What is your name? ')\nprint(f'Hello, {name}!')",
            "language": "python-ds",
            "student_id": "019efa0f-d6c8-7a1d-ab32-f97ba7672f98",
            "course_code": "CS101",
            "mode": "interactive"
        }))

        async for msg in ws:
            data = json.loads(msg)
            status = data.get("status")
            chunk = data.get("chunk", "") or data.get("stdout_output", "")
            print(f"[{status}] {chunk}", end="")

            # When you see a prompt asking for input, send it
            if "What is your name" in data.get("stdout_output", ""):
                await ws.send(json.dumps({"stdin_data": "Alice\n"}))

            if status in ("completed", "error"):
                break

asyncio.run(run())