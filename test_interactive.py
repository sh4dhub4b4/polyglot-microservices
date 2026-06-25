import asyncio, json, websockets

async def test_interactive():
    uri = "ws://localhost:8081/ws/execute"
    async with websockets.connect(uri) as ws:
        payload = json.dumps({
            "source_code": "x = input('Enter something: ')\nprint(f'You entered: {x}')",
            "language": "python-ds",
            "student_id": "019efa0f-d6c8-7a1d-ab32-f97ba7672f98",
            "course_code": "CS101",
            "mode": "interactive",
            "stdin_data": ""
        })
        await ws.send(payload)
        print("[SENT] Execution request")

        stdin_sent = False

        async def receiver():
            nonlocal stdin_sent
            async for msg in ws:
                data = json.loads(msg)
                status = data.get("status")
                output = data.get("stdout_output", "")
                print(f"[{status}] {output}")
                if "Enter something" in output and not stdin_sent:
                    stdin_sent = True
                    await ws.send(json.dumps({"stdin_data": "Hello from Polyglot!\n"}))
                    print("[SENT] stdin data")
                if status in ("completed", "compile_error", "timeout", "error"):
                    if data.get("stdout_output"):
                        print(f"[STDOUT] {data['stdout_output']}")
                    if data.get("stderr_output"):
                        print(f"[STDERR] {data['stderr_output']}")
                    return

        await asyncio.wait_for(receiver(), timeout=30)

asyncio.run(test_interactive())
