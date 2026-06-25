import pytest
from use_cases.local_executor import execute_cpp, execute_python, execute_local


class TestLocalExecutor:

    def test_cpp_hello(self):
        code = '#include <iostream>\nint main() { std::cout << "hello"; }'
        result = execute_cpp(code)
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.execution_time_ms > 0

    def test_cpp_with_stdin(self):
        code = '#include <iostream>\nint main() { int x; std::cin >> x; std::cout << x * 2; }'
        result = execute_cpp(code, stdin_input="21")
        assert result.exit_code == 0
        assert result.stdout.strip() == "42"

    def test_cpp_compile_error(self):
        code = 'int main() { this is not valid c++ }'
        result = execute_cpp(code)
        assert result.exit_code != 0
        assert len(result.stderr) > 0

    def test_python_hello(self):
        code = 'print("hello from python")'
        result = execute_python(code)
        assert result.exit_code == 0
        assert "hello from python" in result.stdout

    def test_python_with_stdin(self):
        code = 'n = int(input())\nprint(n * 3)'
        result = execute_python(code, stdin_input="7")
        assert result.exit_code == 0
        assert result.stdout.strip() == "21"

    def test_execute_local_dispatches_correctly(self):
        result = execute_local('print("hi")', "python")
        assert result.exit_code == 0
        assert "hi" in result.stdout

    def test_execute_local_unsupported_language(self):
        result = execute_local("code", "some-unknown-lang")
        assert result.exit_code == 1
        assert "not supported" in result.stderr
