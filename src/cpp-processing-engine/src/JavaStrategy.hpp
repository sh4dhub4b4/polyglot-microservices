#pragma once
#include "IExecutionStrategy.hpp"
#include "SecurityContainer.hpp"
#include <unistd.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <iostream>

class JavaStrategy : public IExecutionStrategy
{
public:
    bool compile(const std::string &source_code, std::string &compile_errors) override
    {
        std::ofstream out("/tmp/Main.java");
        out << source_code;
        out.close();
        std::remove("/tmp/compile_err.txt");

        pid_t pid = fork();
        if (pid == 0)
        {
            // 🚀 SRE HACK: Route BOTH Stdout and Stderr to the same error file!
            int fd = open("/tmp/compile_err.txt", O_WRONLY | O_CREAT | O_TRUNC, 0666);
            dup2(fd, STDOUT_FILENO);
            dup2(fd, STDERR_FILENO);
            close(fd);
            execlp("javac", "javac", "/tmp/Main.java", nullptr);
            // If execlp fails, it will print here and be captured!
            std::cout << "[System] Fatal: javac compiler failed to launch." << std::endl;
            exit(1);
        }
        else
        {
            int status;
            waitpid(pid, &status, 0);
            if (WEXITSTATUS(status) != 0)
            {
                compile_errors = read_file("/tmp/compile_err.txt");
                return false; // Compilation failed!
            }
        }
        return true;
    }

    ExecutionResult execute(const std::string &source_code, const std::string &stdin_data, int timeout_ms) override
    {
        ExecutionResult result = {0, "", "", 0.0, false, false};
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
                // We enforce a hard limit of 256MB for the JVM heap so it doesn't try to allocate 1GB and crash 
                // due to our SecurityContainer memory limits.
                execlp("java", "java", "-Xmx128m", "-Xms32m", "-XX:MaxMetaspaceSize=64m", "-XX:CompressedClassSpaceSize=32m", "-XX:ReservedCodeCacheSize=32m", "-XX:+UseSerialGC", "-Xss256k", "-cp", "/tmp", "Main", nullptr);
                std::cerr << "[System] Failed to execute the compiled Java binary." << std::endl;
                exit(1);
            }
            catch (const std::exception &e)
            {
                // 🚀 FIX: No more silent deaths! Catch kernel security errors.
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
                result.stderr_output += "\n[System] Crashed/Killed " + std::to_string(WTERMSIG(status));
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
        return result;
    }
};