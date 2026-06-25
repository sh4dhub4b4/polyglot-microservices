import asyncio, json, websockets, sys

async def run(code: str, lang: str, sid: str):
    async with websockets.connect("ws://localhost:8080/ws/execute") as ws:
        await ws.send(json.dumps({
            "source_code": code, "language": lang,
            "student_id": sid, "course_code": "CS101", "mode": "interactive"
        }))

        done = asyncio.Event()

        async def reader():
            async for msg in ws:
                d = json.loads(msg)
                s = d.get("status")
                chunk = d.get("chunk", "") or d.get("stdout_output", "") or d.get("message", "")
                if chunk:
                    print(chunk, end="", flush=True)
                if s in ("completed", "compile_error", "timeout", "error"):
                    done.set()
                    return

        async def writer():
            loop = asyncio.get_running_loop()
            while not done.is_set():
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if done.is_set():
                    break
                await ws.send(json.dumps({"stdin_data": line}))

        reader_task = asyncio.create_task(reader())
        writer_task = asyncio.create_task(writer())
        await asyncio.wait([reader_task, writer_task], return_when=asyncio.FIRST_COMPLETED)
        done.set()
        writer_task.cancel()
        try:
            await writer_task
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else 'x = input("Enter something: "); print(f"You entered: {x}")'
    lang = sys.argv[2] if len(sys.argv) > 2 else "python-ds"
    sid = sys.argv[3] if len(sys.argv) > 3 else "019efa0f-d6c8-7a1d-ab32-f97ba7672f98"
    try:
        asyncio.run(run(code, lang, sid))
    except KeyboardInterrupt:
        pass
