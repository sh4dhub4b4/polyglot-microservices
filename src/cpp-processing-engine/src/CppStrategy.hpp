#pragma once
#include "IExecutionStrategy.hpp"
#include "SecurityContainer.hpp"
#include <unistd.h>
#include <sys/wait.h>
#include <string.h>

class CppStrategy : public IExecutionStrategy {
public:
    bool compile(const std::string &source_code, std::string &compile_errors) override {
        // 1. Write the C++ source code to a file
        std::ofstream out("/tmp/main.cpp");
        out << source_code;
        out.close();

        std::remove("/tmp/compile_err.txt");

        // 2. Fork and run g++ compiler
        pid_t pid = fork();
        if (pid == 0) {
            freopen("/tmp/compile_err.txt", "w", stderr); // Catch compiler errors
            execlp("g++", "g++", "-O2", "-std=c++17", "/tmp/main.cpp", "-o", "/tmp/student_exec", nullptr);
            exit(1);
        } else {
            int status;
            waitpid(pid, &status, 0);
            if (WEXITSTATUS(status) != 0) {
                compile_errors = read_file("/tmp/compile_err.txt");
                return false; // Compilation failed!
            }
        }
        return true; // Compiled successfully
    }

    ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) override {
        ExecutionResult result = {0, "", "", 0.0, false, false};

        std::ofstream in("/tmp/in.txt");
        in << stdin_data;
        in.close();

        std::remove("/tmp/out.txt");
        std::remove("/tmp/err.txt");

        pid_t pid = fork();
        if (pid == 0) {
            try {
                freopen("/tmp/in.txt", "r", stdin);
                freopen("/tmp/out.txt", "w", stdout);
                freopen("/tmp/err.txt", "w", stderr);

                SecurityContainer::enforce_limits();
                execlp("/tmp/student_exec", "student_exec", nullptr); // 👈 Executes the compiled binary
                exit(1);
            } catch (...) { exit(1); }
        } else if (pid > 0) {
            int status;
            waitpid(pid, &status, 0);

            result.stdout_output = read_file("/tmp/out.txt");
            result.stderr_output = read_file("/tmp/err.txt");

            if (WIFSIGNALED(status)) {
                result.exit_code = 128 + WTERMSIG(status);
                result.stderr_output += "\n[System] Process crashed with signal " + std::to_string(WTERMSIG(status));
                if (WTERMSIG(status) == SIGKILL) {
                    result.memory_limit_exceeded = true;
                    result.stderr_output += " (Resource Limit Reached)";
                }
            } else {
                result.exit_code = WEXITSTATUS(status);
            }
        }
        return result;
    }
};