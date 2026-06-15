#pragma once
#include "SecurityContainer.hpp"
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <string>
#include <vector>
#include <iostream>
#include <cerrno>
#include <cstring>
#include <chrono>

/**
 * @class ProcessPipe
 * @brief Manages a child process with real-time, non-blocking I/O via POSIX pipes.
 * 
 * Replaces the legacy file-based I/O pattern (/tmp/in.txt → waitpid → /tmp/out.txt)
 * with live pipe-based streaming. The parent process can write to the child's stdin
 * and read from stdout/stderr without blocking, enabling real-time interactive terminals.
 * 
 * Security: SecurityContainer::enforce_limits() is applied inside the child process
 * after fork(), maintaining identical sandboxing to the batch execution path.
 * 
 * Lifecycle: spawn() → write_stdin()/read_stdout()/read_stderr() → has_exited() → cleanup via destructor
 */
class ProcessPipe
{
public:
    ProcessPipe() = default;

    // Non-copyable (owns file descriptors and child PID)
    ProcessPipe(const ProcessPipe &) = delete;
    ProcessPipe &operator=(const ProcessPipe &) = delete;

    ~ProcessPipe()
    {
        terminate();
        close_all_fds();
    }

    /**
     * @brief Spawns a child process with the given command, connected via pipes.
     * 
     * Creates three pipe pairs (stdin, stdout, stderr), forks the process,
     * applies SecurityContainer limits in the child, and execvp's the command.
     * Parent-side read fds are set to O_NONBLOCK.
     * 
     * @param command The command + arguments to execute (e.g., {"/tmp/student_exec"})
     * @param setup_env Optional lambda to call in the child before exec (for env vars)
     * @return true if fork and exec succeeded, false on failure
     */
    bool spawn(const std::vector<std::string> &command,
               std::function<void()> setup_env = nullptr)
    {
        // Create three pipe pairs: stdin, stdout, stderr
        if (pipe(stdin_pipe_) < 0 || pipe(stdout_pipe_) < 0 || pipe(stderr_pipe_) < 0)
        {
            std::cerr << "[ProcessPipe] Failed to create pipes: " << strerror(errno) << std::endl;
            return false;
        }

        child_pid_ = fork();

        if (child_pid_ < 0)
        {
            std::cerr << "[ProcessPipe] Failed to fork: " << strerror(errno) << std::endl;
            close_all_fds();
            return false;
        }

        if (child_pid_ == 0)
        {
            // ═══════════════════════════════════════
            // CHILD PROCESS
            // ═══════════════════════════════════════

            // Wire pipes to standard file descriptors
            dup2(stdin_pipe_[0], STDIN_FILENO);   // Child reads from stdin pipe
            dup2(stdout_pipe_[1], STDOUT_FILENO); // Child writes to stdout pipe
            dup2(stderr_pipe_[1], STDERR_FILENO); // Child writes to stderr pipe

            // Close all pipe ends (already dup2'd the ones we need)
            close(stdin_pipe_[0]);
            close(stdin_pipe_[1]);
            close(stdout_pipe_[0]);
            close(stdout_pipe_[1]);
            close(stderr_pipe_[0]);
            close(stderr_pipe_[1]);

            // 🛡️ Apply the full security sandbox (Seccomp, rlimits, mount namespace, privilege drop)
            // This is the SAME SecurityContainer used in the batch execution path
            try
            {
                SecurityContainer::enforce_limits();
            }
            catch (const std::exception &e)
            {
                std::cerr << "[Security Kernel] " << e.what() << std::endl;
                _exit(1);
            }

            // Apply strategy-specific environment setup (e.g., JAVA_TOOL_OPTIONS)
            if (setup_env)
            {
                setup_env();
            }

            // Build the execvp argument array
            std::vector<char *> args;
            for (const auto &arg : command)
            {
                args.push_back(const_cast<char *>(arg.c_str()));
            }
            args.push_back(nullptr);

            execvp(args[0], args.data());

            // If execvp returns, it failed
            std::cerr << "[ProcessPipe] Failed to exec: " << strerror(errno) << std::endl;
            _exit(1);
        }

        // ═══════════════════════════════════════
        // PARENT PROCESS
        // ═══════════════════════════════════════

        // Close the child's ends of the pipes
        close(stdin_pipe_[0]);   // Parent doesn't read from stdin pipe
        close(stdout_pipe_[1]); // Parent doesn't write to stdout pipe
        close(stderr_pipe_[1]); // Parent doesn't write to stderr pipe

        // Mark as closed so destructor doesn't double-close
        stdin_pipe_[0] = -1;
        stdout_pipe_[1] = -1;
        stderr_pipe_[1] = -1;

        // Set stdout and stderr reads to non-blocking (critical for WS event loop)
        set_nonblocking(stdout_pipe_[0]);
        set_nonblocking(stderr_pipe_[0]);

        spawned_ = true;
        start_time_ = std::chrono::steady_clock::now();
        last_io_time_ = start_time_;

        return true;
    }

    /**
     * @brief Writes data to the child process's stdin.
     * @return Number of bytes written, or -1 on error.
     */
    ssize_t write_stdin(const std::string &data)
    {
        if (!spawned_ || stdin_pipe_[1] < 0)
            return -1;

        last_io_time_ = std::chrono::steady_clock::now();

        ssize_t written = write(stdin_pipe_[1], data.c_str(), data.size());
        if (written < 0 && errno != EAGAIN)
        {
            std::cerr << "[ProcessPipe] stdin write error: " << strerror(errno) << std::endl;
        }
        return written;
    }

    /**
     * @brief Closes the child's stdin pipe (signals EOF to the child).
     * Call this when no more input will be sent (e.g., for non-interactive programs).
     */
    void close_stdin()
    {
        if (stdin_pipe_[1] >= 0)
        {
            close(stdin_pipe_[1]);
            stdin_pipe_[1] = -1;
        }
    }

    /**
     * @brief Non-blocking read from the child's stdout.
     * @return Data read, or empty string if nothing available.
     */
    std::string read_stdout()
    {
        return read_fd(stdout_pipe_[0]);
    }

    /**
     * @brief Non-blocking read from the child's stderr.
     * @return Data read, or empty string if nothing available.
     */
    std::string read_stderr()
    {
        return read_fd(stderr_pipe_[0]);
    }

    /**
     * @brief Checks if the child process has exited (non-blocking).
     * Updates internal exit code if the child has finished.
     */
    bool has_exited()
    {
        if (exited_)
            return true;
        if (child_pid_ <= 0)
            return true;

        int status;
        pid_t result = ::waitpid(child_pid_, &status, WNOHANG);

        if (result == 0)
            return false; // Still running

        if (result > 0)
        {
            exited_ = true;
            if (WIFEXITED(status))
            {
                exit_code_ = WEXITSTATUS(status);
            }
            else if (WIFSIGNALED(status))
            {
                exit_code_ = 128 + WTERMSIG(status);
                if (WTERMSIG(status) == SIGKILL)
                {
                    memory_limit_exceeded_ = true;
                }
            }
            return true;
        }

        // waitpid error
        exited_ = true;
        exit_code_ = -1;
        return true;
    }

    /**
     * @brief Checks if the idle timeout has been exceeded.
     * @param timeout_ms Maximum milliseconds of inactivity before timeout.
     */
    bool is_timed_out(int timeout_ms = 15000) const
    {
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                           std::chrono::steady_clock::now() - last_io_time_)
                           .count();
        return elapsed > timeout_ms;
    }

    int exit_code() const { return exit_code_; }
    bool memory_limit_exceeded() const { return memory_limit_exceeded_; }
    bool is_spawned() const { return spawned_; }

    /**
     * @brief Forcefully terminates the child process.
     */
    void terminate()
    {
        if (child_pid_ > 0 && !exited_)
        {
            kill(child_pid_, SIGKILL);
            int status;
            ::waitpid(child_pid_, &status, 0); // Reap zombie
            exited_ = true;
            exit_code_ = 999; // 128 + SIGKILL(9) -> changed to 999 to trace callers
        }
    }

private:
    pid_t child_pid_ = -1;
    bool spawned_ = false;
    bool exited_ = false;
    int exit_code_ = -1;
    bool memory_limit_exceeded_ = false;

    // Pipe file descriptors: [0] = read end, [1] = write end
    int stdin_pipe_[2] = {-1, -1};
    int stdout_pipe_[2] = {-1, -1};
    int stderr_pipe_[2] = {-1, -1};

    std::chrono::steady_clock::time_point start_time_;
    std::chrono::steady_clock::time_point last_io_time_;

    static constexpr size_t READ_BUFFER_SIZE = 4096;

    void set_nonblocking(int fd)
    {
        int flags = fcntl(fd, F_GETFL, 0);
        if (flags >= 0)
        {
            fcntl(fd, F_SETFL, flags | O_NONBLOCK);
        }
    }

    std::string read_fd(int fd)
    {
        if (fd < 0)
            return "";

        char buffer[READ_BUFFER_SIZE];
        std::string result;

        while (true)
        {
            ssize_t n = read(fd, buffer, READ_BUFFER_SIZE);
            if (n > 0)
            {
                result.append(buffer, n);
                last_io_time_ = std::chrono::steady_clock::now();
            }
            else if (n == 0)
            {
                break; // EOF — child closed this pipe
            }
            else
            {
                if (errno == EAGAIN || errno == EWOULDBLOCK)
                {
                    break; // No data available right now (non-blocking)
                }
                break; // Read error
            }
        }
        return result;
    }

    void close_all_fds()
    {
        auto safe_close = [](int &fd)
        {
            if (fd >= 0)
            {
                close(fd);
                fd = -1;
            }
        };
        safe_close(stdin_pipe_[0]);
        safe_close(stdin_pipe_[1]);
        safe_close(stdout_pipe_[0]);
        safe_close(stdout_pipe_[1]);
        safe_close(stderr_pipe_[0]);
        safe_close(stderr_pipe_[1]);
    }
};
