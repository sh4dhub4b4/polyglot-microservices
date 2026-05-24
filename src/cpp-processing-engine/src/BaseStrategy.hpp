#pragma once
#include "IExecutionStrategy.hpp"
#include "SecurityContainer.hpp"
#include <unistd.h>
#include <sys/wait.h>
#include <string.h>
#include <fcntl.h>
#include <iostream>
#include <chrono>
#include <vector>
#include <stdlib.h>

class BaseStrategy : public IExecutionStrategy
{
protected:
    virtual std::string get_source_file_path() const = 0;
    virtual std::vector<std::string> get_compile_command() const = 0;
    virtual std::vector<std::string> get_execute_command() const = 0;
    
    // Optional hook for setting environment variables before exec
    virtual void setup_environment() const {}

public:
    bool compile(const std::string &source_code, std::string &compile_errors) override
    {
        auto compile_cmd = get_compile_command();
        if (compile_cmd.empty()) {
            return true; // Interpreted language, no compilation needed
        }

        std::string binary_path = get_compiled_binary_path();
        std::string cache_path;
        if (!binary_path.empty()) {
            size_t hash = std::hash<std::string>{}(source_code);
            cache_path = "/tmp/jit_" + std::to_string(hash) + "_" + std::to_string(source_code.length()) + ".bin";
            
            if (access(cache_path.c_str(), F_OK) == 0) {
                // ⚡ JIT CACHE HIT
                std::string copy_cmd = "cp " + cache_path + " " + binary_path;
                system(copy_cmd.c_str());
                std::cout << "⚡ [JIT CACHE HIT] Skipped Compilation." << std::endl;
                return true;
            }
        }

        std::ofstream out(get_source_file_path());
        out << source_code;
        out.close();

        std::remove("/tmp/compile_err.txt");

        pid_t pid = fork();
        if (pid == 0)
        {
            int fd = open("/tmp/compile_err.txt", O_WRONLY | O_CREAT | O_TRUNC, 0666);
            dup2(fd, STDOUT_FILENO);
            dup2(fd, STDERR_FILENO);
            close(fd);

            setup_environment();

            std::vector<char*> args;
            for (const auto& arg : compile_cmd) {
                args.push_back(const_cast<char*>(arg.c_str()));
            }
            args.push_back(nullptr);

            execvp(args[0], args.data());

            std::cout << "[System] Fatal: Compiler failed to launch." << std::endl;
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
            
            if (!binary_path.empty()) {
                std::string save_cmd = "cp " + binary_path + " " + cache_path;
                system(save_cmd.c_str());
                std::cout << "💾 [JIT CACHE SAVED] Binary cached in RAM-Disk." << std::endl;
            }
        }
        return true;
    }

    ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) override
    {
        ExecutionResult result = {0, "", "", 0.0, false, false};

        // If interpreted, write source code here (compiled languages already did this)
        if (get_compile_command().empty()) {
            std::ofstream out(get_source_file_path());
            out << source_code;
            out.close();
        }

        std::ofstream in("/tmp/in.txt");
        in << stdin_data;
        in.close();

        std::remove("/tmp/out.txt");
        std::remove("/tmp/err.txt");

        auto start_time = std::chrono::steady_clock::now();

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
                setup_environment();

                auto exec_cmd = get_execute_command();
                std::vector<char*> args;
                for (const auto& arg : exec_cmd) {
                    args.push_back(const_cast<char*>(arg.c_str()));
                }
                args.push_back(nullptr);

                execvp(args[0], args.data());

                std::cerr << "[System] Failed to execute the binary." << std::endl;
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
            int status;
            waitpid(pid, &status, 0);

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
        else
        {
            result.stderr_output = "Failed to fork sandbox process.";
            result.exit_code = -1;
        }

        auto end_time = std::chrono::steady_clock::now();
        result.execution_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();

        return result;
    }
};
