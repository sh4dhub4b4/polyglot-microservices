#pragma once
#include <string>
#include <fstream>
#include <sstream>

// Helper function ekhane niye ashlam jate C++ ar Python duijon e use korte pare
inline std::string read_file(const std::string &path) {
    std::ifstream file(path);
    if (!file.is_open()) return "";
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

struct ExecutionResult {
    int exit_code;
    std::string stdout_output;
    std::string stderr_output;
    double execution_time_ms;
    bool memory_limit_exceeded;
    bool compilation_failed; // 👈 NEW: Build error ar Runtime error alada korar jonno
};

class IExecutionStrategy {
public:
    virtual ~IExecutionStrategy() = default;
    
    // Stage 1: Returns true if compilation succeeds. Does nothing for Python.
    virtual bool compile(const std::string &source_code, std::string &compile_errors) = 0;
    
    // Stage 2: Executes the binary or script
    virtual ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) = 0;
};