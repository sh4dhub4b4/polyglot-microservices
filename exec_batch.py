import asyncio, json, websockets, sys

async def run(code: str, lang: str, sid: str):
    print(f"[exec] Connecting to ws://localhost:8080/ws/execute ...")
    async with websockets.connect("ws://localhost:8080/ws/execute") as ws:
        await ws.send(json.dumps({
            "source_code": code, "language": lang,
            "student_id": sid, "course_code": "CS101", "mode": "batch"
        }))
        try:
            async with asyncio.timeout(60):
                async for msg in ws:
                    d = json.loads(msg)
                    s = d.get("status")
                    out = d.get("stdout","") or d.get("stdout_output","")
                    err = d.get("stderr","") or d.get("stderr_output","")
                    msg_text = d.get("message","")
                    if out: print(f"[{s}] {out}", end="")
                    if err: print(f"[{s}] {err}", end="", file=sys.stderr)
                    if msg_text and not out and not err: print(f"[{s}] {msg_text}")
                    if s in ("completed","error"): break
        except asyncio.TimeoutError:
            print("[exec] TIMEOUT: No response in 60s. Is make dev-orchestrator running?")

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "print(42)"
    lang = sys.argv[2] if len(sys.argv) > 2 else "python-ds"
    sid = sys.argv[3] if len(sys.argv) > 3 else "019efa0f-d6c8-7a1d-ab32-f97ba7672f98"
    print(f"[exec] code={code!r}, lang={lang}")
    asyncio.run(run(code, lang, sid))
