#pragma once
#include "IExecutionStrategy.hpp"
#include "SecurityContainer.hpp"
#include <unistd.h>
#include <sys/wait.h>
#include <string.h>

class PythonStrategy : public IExecutionStrategy
{
public:
    // 👈 NEW: Python er compile lagena, tai direct true
    bool compile(const std::string &source_code, std::string &compile_errors) override {
        return true; 
    }

    ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) override
    {
        // 👈 Update: initialize with false for compilation_failed
        ExecutionResult result = {0, "", "", 0.0, false, false}; 

        // 1. Write the source code
        std::string filename = "/tmp/sandbox_exec.py";
        std::ofstream out(filename);
        out << source_code;
        out.close();

        // 2. Write the standard input data BEFORE forking (Security Best Practice)
        std::ofstream in("/tmp/in.txt");
        in << stdin_data;
        in.close();

        std::remove("/tmp/out.txt");
        std::remove("/tmp/err.txt");

        pid_t pid = fork();

        if (pid == 0) // Child Process
        {
            try
            {
                // 3. Map standard streams to files
                freopen("/tmp/in.txt", "r", stdin); // Python will read input from here

                // ✅ Hardened Production-Ready Code:
                if (freopen("/tmp/out.txt", "w", stdout) == nullptr)
                {
                    throw std::runtime_error("Critical Error: Failed to redirect stdout to /tmp/out.txt. Possible filesystem permission issue.");
                }

                if (freopen("/tmp/err.txt", "w", stderr) == nullptr)
                {
                    throw std::runtime_error("Critical Error: Failed to redirect stderr to /tmp/err.txt. Possible filesystem permission issue.");
                }

                // 4. Lock down the container
                SecurityContainer::enforce_limits();

                // 5. Execute using OS path lookup
                execlp("python3", "python3", "-u", filename.c_str(), nullptr);

                std::cerr << "Sandbox Error: execl failed. Reason: " << strerror(errno) << std::endl;
                exit(1);
            }
            catch (const std::exception &e)
            {
                std::cerr << "Sandbox Exception: " << e.what() << std::endl;
                exit(1);
            }
        }
        else if (pid > 0) // Parent Process
        {
            int status;
            waitpid(pid, &status, 0);

            result.stdout_output = read_file("/tmp/out.txt");
            /*
            // 🚀 DEBUG INJECTION: C++ directly error stream-e stdin_data dhukiye dibe
            result.stderr_output = "[C++ DEBUG] Length of stdin_data: " + std::to_string(stdin_data.length()) + "\n" +
                                   "[C++ DEBUG] Content of stdin_data: '" + stdin_data + "'\n" +
                                   "--- Original Exec Errors ---\n" +
                                   read_file("/tmp/err.txt");

            */

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
        else
        {
            result.stderr_output = "Failed to fork sandbox process.";
            result.exit_code = -1;
        }

        return result;
    }
};