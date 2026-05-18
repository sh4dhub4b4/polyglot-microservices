#pragma once
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#include <iostream>
#include <stdexcept>

class SecurityContainer
{
public:
    // Define the strict limits for student code execution
    static constexpr int MAX_MEMORY_MB = 512;
    static constexpr int MAX_CPU_TIME_SEC = 5;
    static constexpr int MAX_FILE_SIZE_MB = 1; // Prevent filling up the hard drive

    // The restricted user ID (must be created in the Dockerfile, e.g., 'sandboxuser')
    static constexpr uid_t SANDBOX_UID = 10002;
    static constexpr gid_t SANDBOX_GID = 10002;

    static void enforce_limits()
    {
        struct rlimit rl;

        // 1. Limit Memory (RAM + Swap)
        rl.rlim_cur = rl.rlim_max = MAX_MEMORY_MB * 1024 * 1024;
        if (setrlimit(RLIMIT_AS, &rl) != 0)
            throw std::runtime_error("Failed to limit Memory");

        // 2. Limit CPU Time
        rl.rlim_cur = rl.rlim_max = MAX_CPU_TIME_SEC;
        if (setrlimit(RLIMIT_CPU, &rl) != 0)
            throw std::runtime_error("Failed to limit CPU");

        // 3. Limit File Output Size
        rl.rlim_cur = rl.rlim_max = MAX_FILE_SIZE_MB * 1024 * 1024;
        if (setrlimit(RLIMIT_FSIZE, &rl) != 0)
            throw std::runtime_error("Failed to limit File Size");

        // 4. Drop Root Privileges (Cannot reverse this once dropped)
        if (setgid(SANDBOX_GID) != 0)
            throw std::runtime_error("Failed to drop GID privileges");
        if (setuid(SANDBOX_UID) != 0)
            throw std::runtime_error("Failed to drop UID privileges");
    }
};