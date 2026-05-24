#pragma once
#include <string>
#include <fstream>
#include <sstream>
#include <chrono>
#include <thread>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h> // Must be included BEFORE the macro hack

// Helper function ekhane niye ashlam jate C++ ar Python duijon e use korte pare
inline std::string read_file(const std::string &path)
{
    std::ifstream file(path);
    if (!file.is_open())
        return "";
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

// 🚀 THE MAGIC: Mother-level system call interceptor
inline pid_t smart_waitpid(pid_t pid, int *status, int options)
{
    // Check if the parent process is a compiler (gcc/go/g++)
    // SRE NOTE: Compilation is intensive, 5s might be too short for slow CPUs
    auto start_time = std::chrono::steady_clock::now();
    while (true)
    {
        // Use :: to call the real OS waitpid, bypassing the macro
        pid_t res = ::waitpid(pid, status, WNOHANG);
        if (res != 0)
            return res; // Process finished naturally or system error

        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                           std::chrono::steady_clock::now() - start_time)
                           .count();

        if (elapsed > 15000)
        { // Universal 15-second timeout
            kill(pid, SIGKILL);
            ::waitpid(pid, status, 0); // Clean up the zombie process

            // Inject timeout message into the error file.
            // The child strategies will read this naturally without needing code changes!
            std::ofstream err_file("/tmp/err.txt", std::ios_base::app);
            err_file << "\n[System] ⏱️ Execution timed out! Infinite loop killed by Mother Strategy.";
            err_file.close();

            return pid;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

// 🛑 MACRO HIJACK: Forces all child files to use our smart_waitpid instead of the OS one
#define waitpid(pid, status, options) smart_waitpid(pid, status, options)

struct ExecutionResult
{
    int exit_code;
    std::string stdout_output;
    std::string stderr_output;
    double execution_time_ms;
    bool memory_limit_exceeded;
    bool compilation_failed; // 👈 NEW: Build error ar Runtime error alada korar jonno
};

class IExecutionStrategy
{
public:
    virtual ~IExecutionStrategy() = default;

    // Stage 1: Returns true if compilation succeeds. Does nothing for Python.
    virtual bool compile(const std::string &source_code, std::string &compile_errors) = 0;

    // Stage 2: Executes the binary or script
    virtual ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) = 0;

    // Stage 3 (Optional): Used by BaseStrategy to cache compiled binaries to RAM-Disk
    virtual std::string get_compiled_binary_path() const { return ""; }
};