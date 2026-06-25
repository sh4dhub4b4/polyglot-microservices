import asyncio, json, websockets

async def test():
    async with websockets.connect("ws://localhost:8081/ws/execute") as ws:
        await ws.send(json.dumps({
            "source_code": "print('Hello from batch!')",
            "language": "python-ds",
            "student_id": "019efa0f-d6c8-7a1d-ab32-f97ba7672f98",
            "course_code": "CS101",
            "mode": "batch"
        }))
        async for msg in ws:
            data = json.loads(msg)
            s = data.get("status")
            out = data.get("stdout_output","") or data.get("stdout","")
            err = data.get("stderr_output","") or data.get("stderr","")
            print(f"[{s}] {out}{err}")
            if s in ("completed","error"):
                break

asyncio.run(test())
