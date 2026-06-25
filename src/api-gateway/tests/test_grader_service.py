import json
import pytest
from use_cases.grader_service import run_grader, GradeResult


class TestGraderService:

    def test_cpp_all_pass(self):
        code = '#include <iostream>\nint main() { int x; std::cin >> x; std::cout << x + 1; }'
        tests = json.dumps([{"stdin": "5", "expected_stdout": "6"}, {"stdin": "0", "expected_stdout": "1"}])
        result = run_grader(code, "cpp-basic", tests, max_marks=100)
        assert result.tests_passed == 2
        assert result.tests_total == 2
        assert result.marks_awarded == 100.0

    def test_cpp_some_fail(self):
        code = '#include <iostream>\nint main() { std::cout << "wrong"; }'
        tests = json.dumps([{"stdin": "", "expected_stdout": "hello"}, {"stdin": "", "expected_stdout": "wrong"}])
        result = run_grader(code, "cpp-basic", tests, max_marks=100)
        assert result.tests_passed == 1
        assert result.tests_total == 2
        assert result.marks_awarded == 50.0

    def test_python_all_pass(self):
        code = 'n = int(input())\nprint(n * 2)'
        tests = json.dumps([{"stdin": "5", "expected_stdout": "10"}, {"stdin": "21", "expected_stdout": "42"}])
        result = run_grader(code, "python", tests, max_marks=100)
        assert result.tests_passed == 2

    def test_no_test_cases(self):
        result = run_grader("int main(){}", "cpp-basic", "[]", max_marks=50)
        assert result.tests_total == 0
        assert result.marks_awarded == 50.0

    def test_empty_source_code_fails(self):
        code = 'int main() { return 1; }'
        tests = json.dumps([{"stdin": "", "expected_stdout": "hello"}])
        result = run_grader(code, "cpp-basic", tests, max_marks=10)
        assert result.tests_passed == 0
        assert result.marks_awarded == 0.0

    def test_cpp_compile_error_returns_stderr(self):
        code = 'int main() { this is not valid c++ }'
        tests = json.dumps([{"stdin": "", "expected_stdout": "hello"}])
        result = run_grader(code, "cpp-basic", tests, max_marks=10)
        assert result.tests_passed == 0
        assert "compilation failed" in result.stderr.lower() or "error" in result.stderr.lower() or "expected" in result.stderr.lower()
