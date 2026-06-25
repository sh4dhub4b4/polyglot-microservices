import subprocess
import tempfile
import os
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class GradeResult:
    tests_passed: int = 0
    tests_total: int = 0
    stdout: str = ""
    stderr: str = ""
    grader_feedback: list[str] = field(default_factory=list)
    marks_awarded: float = 0.0


def _run(*args, stdin_input: str = "", timeout: int = 10) -> subprocess.CompletedProcess:
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


def _execute_cpp(source_code: str, stdin_input: str, timeout: int = 10) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "solution.cpp"
        bin_path = Path(tmpdir) / "solution.exe"
        src_path.write_text(source_code)

        compile_proc = _run("g++", "-std=c++17", "-O2", "-o", str(bin_path), str(src_path), timeout=timeout)
        if compile_proc.returncode != 0:
            return "", compile_proc.stderr or "Compilation failed"

        run_proc = _run(str(bin_path), stdin_input=stdin_input, timeout=timeout)
        return run_proc.stdout or "", run_proc.stderr or ""


def _execute_python(source_code: str, stdin_input: str, timeout: int = 10) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "solution.py"
        src_path.write_text(source_code)

        run_proc = _run("python", str(src_path), stdin_input=stdin_input, timeout=timeout)
        return run_proc.stdout or "", run_proc.stderr or ""


def run_grader(
    source_code: str,
    language: str,
    hidden_test_cases: str | list[dict],
    max_marks: float = 100.0,
) -> GradeResult:
    if isinstance(hidden_test_cases, str):
        test_cases = json.loads(hidden_test_cases) if hidden_test_cases else []
    else:
        test_cases = hidden_test_cases or []

    tests_total = len(test_cases)
    tests_passed = 0
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    feedback: list[str] = []

    for i, test in enumerate(test_cases):
        stdin_input = test.get("stdin", "")
        expected = test.get("expected_stdout", "").strip()

        try:
            if language in ("cpp-basic", "c-basic"):
                actual_stdout, actual_stderr = _execute_cpp(source_code, stdin_input)
            elif language == "python":
                actual_stdout, actual_stderr = _execute_python(source_code, stdin_input)
            else:
                feedback.append(f"Test {i+1}: Language '{language}' not supported for local grading.")
                stderr_parts.append(f"Unsupported language: {language}")
                continue

            stdout_parts.append(f"--- Test {i+1} ---\n{actual_stdout}")
            if actual_stderr:
                stderr_parts.append(f"--- Test {i+1} stderr ---\n{actual_stderr}")

            actual_clean = actual_stdout.strip()
            if actual_clean == expected:
                tests_passed += 1
                feedback.append(f"Test {i+1}: PASS")
            else:
                feedback.append(
                    f"Test {i+1}: FAIL — expected '{expected}', got '{actual_clean}'"
                )
        except subprocess.TimeoutExpired:
            feedback.append(f"Test {i+1}: TIMEOUT")
            stderr_parts.append(f"Test {i+1} timed out (>10s)")
        except FileNotFoundError:
            if language in ("cpp-basic", "c-basic"):
                feedback.append(f"Test {i+1}: SKIP — g++ not found on this server")
            else:
                feedback.append(f"Test {i+1}: SKIP — runtime not found")
        except Exception as e:
            feedback.append(f"Test {i+1}: ERROR — {e}")
            stderr_parts.append(str(e))

    marks_awarded = (tests_passed / tests_total * max_marks) if tests_total > 0 else max_marks

    return GradeResult(
        tests_passed=tests_passed,
        tests_total=tests_total,
        stdout="\n".join(stdout_parts),
        stderr="\n".join(stderr_parts),
        grader_feedback=feedback,
        marks_awarded=marks_awarded,
    )
