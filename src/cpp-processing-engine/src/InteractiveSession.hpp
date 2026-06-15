#pragma once
#include "ProcessPipe.hpp"
#include "SandboxOrchestrator.hpp"
#include "json.hpp"
#include <memory>
#include <string>
#include <iostream>

using json = nlohmann::json;

/**
 * @struct CompileResult
 * @brief Encapsulates the outcome of a batch compilation phase.
 */
struct CompileResult
{
    bool success;
    std::string errors; // Compiler stderr output (empty on success)
};

/**
 * @class InteractiveSession
 * @brief Orchestrates a single interactive code execution session.
 * 
 * This is the bridge between a WebSocket connection and the underlying
 * ProcessPipe. It follows the same two-phase model as SandboxOrchestrator:
 *   Phase 1 (Batch):       Compile source code → return errors immediately
 *   Phase 2 (Interactive): Spawn execution via ProcessPipe → stream I/O in real-time
 * 
 * Design Principles:
 *   - Single Responsibility: Manages session lifecycle only, no protocol awareness
 *   - Composition: Delegates compilation to IExecutionStrategy, execution to ProcessPipe
 *   - Encapsulation: Hides pipe/fork complexity behind clean read/write methods
 * 
 * Usage:
 *   InteractiveSession session("cpp");
 *   auto compile = session.compile(source_code);
 *   if (compile.success) {
 *       session.start_execution(source_code);
 *       while (session.is_running()) {
 *           auto out = session.read_stdout();
 *           // ... send to WebSocket ...
 *           // ... receive from WebSocket → session.write_stdin(data) ...
 *       }
 *   }
 */
class InteractiveSession
{
public:
    /**
     * @brief Constructs a session for the given language.
     * 
     * Internally creates the correct IExecutionStrategy via SandboxOrchestrator's
     * language routing logic, ensuring identical language support to the batch path.
     * 
     * @param language The runtime identifier (e.g., "cpp", "python", "java")
     * @throws std::invalid_argument if the language is unsupported
     */
    explicit InteractiveSession(const std::string &language)
        : language_(language)
    {
        // Reuse the SandboxOrchestrator's language → strategy routing
        orchestrator_.set_language(language);
    }

    // Non-copyable (owns unique resources)
    InteractiveSession(const InteractiveSession &) = delete;
    InteractiveSession &operator=(const InteractiveSession &) = delete;

    /**
     * @brief Phase 1: Compiles the source code (batch operation).
     * 
     * Delegates to IExecutionStrategy::compile(). This is synchronous and blocking.
     * For interpreted languages (Python, Node), this is a no-op that returns success.
     * 
     * @param source_code The student's source code to compile
     * @return CompileResult with success flag and any compiler error messages
     */
    CompileResult compile(const std::string &source_code)
    {
        CompileResult result;
        result.success = orchestrator_.compile_only(source_code, result.errors);
        return result;
    }

    bool is_compile_only() const
    {
        return orchestrator_.get_execute_command().empty();
    }

    ExecutionResult execute_only(const std::string &source_code, const std::string &stdin_data)
    {
        return orchestrator_.execute_only(source_code, stdin_data);
    }

    /**
     * @brief Phase 2: Starts interactive execution via ProcessPipe.
     * 
     * Spawns the compiled binary (or interpreter) as a child process connected
     * via POSIX pipes. The child runs inside the SecurityContainer sandbox.
     * 
     * For interpreted languages, the source code is written to the temp file path
     * before spawning (since compile() was a no-op).
     * 
     * @param source_code The source code (needed for interpreted languages)
     * @return true if the process was spawned successfully
     */
    bool start_execution(const std::string &source_code)
    {
        process_ = std::make_unique<ProcessPipe>();

        auto exec_cmd = orchestrator_.get_execute_command();
        auto setup_env = orchestrator_.get_setup_environment_fn();

        // For interpreted languages, write source to the file path the strategy expects
        if (orchestrator_.is_interpreted())
        {
            std::string source_path = orchestrator_.get_source_file_path();
            std::ofstream out(source_path);
            out << source_code;
            out.close();
        }

        return process_->spawn(exec_cmd, setup_env);
    }

    /**
     * @brief Writes user input to the child process's stdin pipe.
     * @param data The raw input data (usually ending with \n)
     */
    void write_stdin(const std::string &data)
    {
        if (process_)
        {
            process_->write_stdin(data);
        }
    }

    /**
     * @brief Closes the child's stdin (signals EOF).
     * Use when no more input will be provided.
     */
    void close_stdin()
    {
        if (process_)
        {
            process_->close_stdin();
        }
    }

    /**
     * @brief Non-blocking read from child's stdout.
     * @return Available stdout data, or empty string if nothing ready.
     */
    std::string read_stdout()
    {
        return process_ ? process_->read_stdout() : "";
    }

    /**
     * @brief Non-blocking read from child's stderr.
     * @return Available stderr data, or empty string if nothing ready.
     */
    std::string read_stderr()
    {
        return process_ ? process_->read_stderr() : "";
    }

    /**
     * @brief Checks if the child process is still running.
     * Also enforces idle timeout — kills the process if inactive too long.
     */
    bool is_running()
    {
        if (!process_ || !process_->is_spawned())
            return false;

        // Enforce idle timeout (same 15s as smart_waitpid in batch mode)
        if (process_->is_timed_out(IDLE_TIMEOUT_MS))
        {
            timed_out_ = true;
            process_->terminate();
        }

        return !process_->has_exited();
    }

    /**
     * @brief Returns the child's exit code (only valid after is_running() returns false).
     */
    int exit_code() const
    {
        return process_ ? process_->exit_code() : -1;
    }

    bool memory_limit_exceeded() const
    {
        return process_ ? process_->memory_limit_exceeded() : false;
    }

    bool timed_out() const { return timed_out_; }

    /**
     * @brief Forcefully terminates the session.
     */
    void terminate()
    {
        if (process_)
        {
            process_->terminate();
        }
    }

private:
    std::string language_;
    SandboxOrchestrator orchestrator_;
    std::unique_ptr<ProcessPipe> process_;
    bool timed_out_ = false;

    static constexpr int IDLE_TIMEOUT_MS = 15000;
};
