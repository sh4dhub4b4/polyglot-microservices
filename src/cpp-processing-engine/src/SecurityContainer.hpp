#pragma once
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#include <iostream>
#include <stdexcept>
#include <seccomp.h> // 👈 NEW: Linux Kernel system call filtering

class SecurityContainer
{
public:
    // Define the strict limits for student code execution
    static constexpr int MAX_MEMORY_MB = 512;
    static constexpr int MAX_CPU_TIME_SEC = 5;
    static constexpr int MAX_FILE_SIZE_MB = 1; // Prevent filling up the hard drive

    // 🚀 NEW: Maximum thread/process count to prevent Fork Bombs
    static constexpr int MAX_PROCESSES = 50;

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

        // 🚀 NEW: 3.5 Limit Number of Processes (Fork Bomb Protection)
        rl.rlim_cur = rl.rlim_max = MAX_PROCESSES;
        if (setrlimit(RLIMIT_NPROC, &rl) != 0)
            throw std::runtime_error("Failed to limit Number of Processes");

        // 4. SECCOMP: Kernel-Level System Call Filtering
        // Initialize the filter to ALLOW all system calls by default...
        scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);
        if (ctx == NULL)
        {
            throw std::runtime_error("Failed to initialize seccomp");
        }

        // This completely neutralizes reverse shells, curl, wget, etc.
        // Ekhon process kill na kore EACCES (Permission Denied) error dibe
        if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EACCES), SCMP_SYS(socket), 0) < 0)
        {
            seccomp_release(ctx);
            throw std::runtime_error("Failed to add seccomp socket rule");
        }

        // Load the filter into the Linux kernel for this process
        if (seccomp_load(ctx) < 0)
        {
            seccomp_release(ctx);
            throw std::runtime_error("Failed to load seccomp filter");
        }
        seccomp_release(ctx);

        // 5. Drop Root Privileges (Cannot reverse this once dropped)
        if (setgid(SANDBOX_GID) != 0)
            throw std::runtime_error("Failed to drop GID privileges");
        if (setuid(SANDBOX_UID) != 0)
            throw std::runtime_error("Failed to drop UID privileges");
    }
};