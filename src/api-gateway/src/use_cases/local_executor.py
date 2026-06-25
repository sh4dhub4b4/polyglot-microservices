import subprocess
import tempfile
from pathlib import Path
import time
import sys


class LocalExecutionResult:
    def __init__(self, stdout: str = "", stderr: str = "", exit_code: int = 0, execution_time_ms: float = 0.0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time_ms = execution_time_ms


def _run(*args, stdin_input: str = "", timeout: int = 15) -> subprocess.CompletedProcess:
    """Cross-platform subprocess runner that handles Windows handle inheritance issues."""
    extra = {}
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        extra["startupinfo"] = si
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        args,
        input=stdin_input,
        capture_output=True,
        text=True,
        timeout=timeout,
        **extra,
    )


def execute_cpp(source_code: str, stdin_input: str = "", timeout: int = 15) -> LocalExecutionResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "solution.cpp"
        bin_path = Path(tmpdir) / "solution.exe"
        src_path.write_text(source_code)

        start = time.perf_counter()
        compile_proc = _run("g++", "-std=c++17", "-O2", "-o", str(bin_path), str(src_path), timeout=timeout)
        if compile_proc.returncode != 0:
            elapsed = (time.perf_counter() - start) * 1000
            return LocalExecutionResult(
                stderr=compile_proc.stderr or "Compilation failed",
                exit_code=compile_proc.returncode,
                execution_time_ms=elapsed,
            )

        run_proc = _run(str(bin_path), stdin_input=stdin_input, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000
        return LocalExecutionResult(
            stdout=run_proc.stdout or "",
            stderr=run_proc.stderr or "",
            exit_code=run_proc.returncode,
            execution_time_ms=elapsed,
        )


def execute_python(source_code: str, stdin_input: str = "", timeout: int = 15) -> LocalExecutionResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "solution.py"
        src_path.write_text(source_code)

        start = time.perf_counter()
        run_proc = _run("python", str(src_path), stdin_input=stdin_input, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000
        return LocalExecutionResult(
            stdout=run_proc.stdout or "",
            stderr=run_proc.stderr or "",
            exit_code=run_proc.returncode,
            execution_time_ms=elapsed,
        )


def execute_local(source_code: str, env_type: str, stdin_input: str = "", timeout: int = 15) -> LocalExecutionResult:
    if env_type in ("cpp-basic", "c-basic"):
        return execute_cpp(source_code, stdin_input, timeout)
    elif env_type in ("python", "python-ds"):
        return execute_python(source_code, stdin_input, timeout)
    else:
        return LocalExecutionResult(
            stderr=f"Local execution not supported for environment type: {env_type}",
            exit_code=1,
        )
