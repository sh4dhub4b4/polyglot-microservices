#pragma once
#include "IExecutionStrategy.hpp"
#include "SecurityContainer.hpp"
#include <unistd.h>
#include <sys/wait.h>
#include <string.h>
#include <fcntl.h>
#include <iostream>
#include <fstream>
#include <chrono>
#include <thread>

class NodeStrategy : public IExecutionStrategy
{
public:
    bool compile(const std::string &source_code, std::string &compile_errors) override
    {
        // Node.js doesn't need compilation, but we validate syntax
        std::ofstream source_file("/tmp/main.js");
        source_file << source_code;
        source_file.close();

        // Quick syntax check using node --check
        std::remove("/tmp/compile_err.txt");

        pid_t pid = fork();
        if (pid == 0)
        {
            int fd = open("/tmp/compile_err.txt", O_WRONLY | O_CREAT | O_TRUNC, 0666);
            dup2(fd, STDOUT_FILENO);
            dup2(fd, STDERR_FILENO);
            close(fd);

            setenv("HOME", "/tmp", 1);
            setenv("NODE_OPTIONS", "--max-old-space-size=512", 1); // Memory limit

            execlp("node", "node", "--check", "/tmp/main.js", nullptr);

            std::cout << "[System] Fatal: node compiler failed to launch." << std::endl;
            exit(1);
        }
        else
        {
            int status;
            waitpid(pid, &status, 0);
            if (WEXITSTATUS(status) != 0)
            {
                compile_errors = read_file("/tmp/compile_err.txt");
                return false;
            }
        }
        return true;
    }

    ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) override
    {
        ExecutionResult result = {0, "", "", 0.0, false, false};
        auto start_time = std::chrono::steady_clock::now();

        // Write stdin data
        std::ofstream in("/tmp/in.txt");
        in << stdin_data;
        in.close();

        std::remove("/tmp/out.txt");
        std::remove("/tmp/err.txt");

        pid_t pid = fork();
        if (pid == 0)
        {
            try
            {
                int fd_in = open("/tmp/in.txt", O_RDONLY);
                int fd_out = open("/tmp/out.txt", O_WRONLY | O_CREAT | O_TRUNC, 0666);
                int fd_err = open("/tmp/err.txt", O_WRONLY | O_CREAT | O_TRUNC, 0666);

                dup2(fd_in, STDIN_FILENO);
                dup2(fd_out, STDOUT_FILENO);
                dup2(fd_err, STDERR_FILENO);

                close(fd_in);
                close(fd_out);
                close(fd_err);

                SecurityContainer::enforce_limits();
                execlp("node", "node", "/tmp/main.js", nullptr);

                std::cerr << "[System] Failed to execute Node.js script." << std::endl;
                exit(1);
            }
            catch (const std::exception &e)
            {
                std::cerr << "[Security Kernel] " << e.what() << std::endl;
                exit(1);
            }
            catch (...)
            {
                std::cerr << "[System] Unknown fatal crash." << std::endl;
                exit(1);
            }
        }
        else if (pid > 0)
        {
            // Add timeout handling
            int status;
            pid_t wait_result;
            auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);

            while (true)
            {
                wait_result = waitpid(pid, &status, WNOHANG);

                if (wait_result == pid)
                {
                    // Process finished
                    break;
                }

                if (wait_result == -1)
                {
                    // Error
                    result.stderr_output = "waitpid failed";
                    result.exit_code = -1;
                    return result;
                }

                // Check timeout
                if (std::chrono::steady_clock::now() > deadline)
                {
                    kill(pid, SIGKILL);
                    waitpid(pid, &status, 0);
                    result.stderr_output = "\n[System] Execution timeout (" + std::to_string(timeout_ms) + "ms)";
                    result.exit_code = 124;
                    result.execution_time_ms = timeout_ms;
                    return result;
                }

                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }

            result.stdout_output = read_file("/tmp/out.txt");
            result.stderr_output = read_file("/tmp/err.txt");

            if (WIFSIGNALED(status))
            {
                result.exit_code = 128 + WTERMSIG(status);
                result.stderr_output += "\n[System] Process crashed with signal " + std::to_string(WTERMSIG(status));
                if (WTERMSIG(status) == SIGKILL)
                {
                    result.memory_limit_exceeded = true;
                    result.stderr_output += " (Resource Limit Reached)";
                }
            }
            else
            {
                result.exit_code = WEXITSTATUS(status);
            }
        }

        auto end_time = std::chrono::steady_clock::now();
        result.execution_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();

        return result;
    }
};