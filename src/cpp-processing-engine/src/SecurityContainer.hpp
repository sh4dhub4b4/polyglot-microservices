#pragma once
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#include <iostream>
#include <stdexcept>
#include <seccomp.h> // Linux Kernel system call filtering
#include <sys/prctl.h>
#include <sched.h>
#include <sys/mount.h>

class SecurityContainer
{
private:
    static constexpr int MAX_MEMORY_MB = 512;
    static constexpr int MAX_CPU_TIME_SEC = 5;
    static constexpr int MAX_FILE_SIZE_MB = 1; 
    static constexpr int MAX_PROCESSES = 50;

    static constexpr uid_t SANDBOX_UID = 10002;
    static constexpr gid_t SANDBOX_GID = 10002;

    static void apply_seccomp_filters()
    {
        // Initialize the filter to ALLOW all system calls by default...
        scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);
        if (ctx == NULL)
        {
            throw std::runtime_error("Failed to initialize seccomp");
        }

        // List of extremely dangerous syscalls to block with EACCES (Permission Denied)
        int syscalls_to_block[] = {
            SCMP_SYS(socket), // Neutralize reverse shells, curl, wget, internet access
            SCMP_SYS(kill),   // Prevent Process Isolation Break (killall engine_binary)
            SCMP_SYS(tkill),
            SCMP_SYS(tgkill),
            SCMP_SYS(ptrace), // Prevent process memory hijacking/debugging
            SCMP_SYS(reboot),
            SCMP_SYS(chroot),
            SCMP_SYS(mount),
            SCMP_SYS(umount2),
            SCMP_SYS(setuid), // Prevent regaining root
            SCMP_SYS(setgid),
            SCMP_SYS(setreuid),
            SCMP_SYS(setregid),
            SCMP_SYS(bpf),
            SCMP_SYS(unshare),
            SCMP_SYS(setns)
        };

        for (int sys_call : syscalls_to_block)
        {
            if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EACCES), sys_call, 0) < 0)
            {
                seccomp_release(ctx);
                throw std::runtime_error("Failed to add seccomp rule");
            }
        }

        // Load the filter into the Linux kernel for this process
        if (seccomp_load(ctx) < 0)
        {
            seccomp_release(ctx);
            throw std::runtime_error("Failed to load seccomp filter");
        }
        seccomp_release(ctx);
    }

    static void apply_rlimits()
    {
        struct rlimit rl;

        // 1. Limit Memory (RAM + Swap)
        rl.rlim_cur = rl.rlim_max = (MAX_MEMORY_MB + 256) * 1024 * 1024;
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

        // 4. Limit Number of Processes (Fork Bomb Protection)
        rl.rlim_cur = rl.rlim_max = MAX_PROCESSES;
        if (setrlimit(RLIMIT_NPROC, &rl) != 0)
            throw std::runtime_error("Failed to limit Number of Processes");
    }

    static void drop_privileges()
    {
        // Drop Root Privileges (Cannot reverse this once dropped)
        if (setgid(SANDBOX_GID) != 0)
            throw std::runtime_error("Failed to drop GID privileges");
        if (setuid(SANDBOX_UID) != 0)
            throw std::runtime_error("Failed to drop UID privileges");
    }

    static void apply_mount_namespace()
    {
        // 1. Create a new independent Mount Namespace
        if (unshare(CLONE_NEWNS) != 0) {
            throw std::runtime_error("Failed to unshare Mount Namespace (Missing CAP_SYS_ADMIN?)");
        }
        
        // Prevent mount propagation back to the host
        if (mount("none", "/", NULL, MS_REC | MS_PRIVATE, NULL) != 0) {
            throw std::runtime_error("Failed to make root private");
        }
        
        // 2. Hide our proprietary C++ Sandbox Engine source/binary
        if (mount("tmpfs", "/app", "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "size=1m") != 0) {
            throw std::runtime_error("Failed to hide /app directory");
        }
        
        // 3. Hide Kubernetes Service Account Tokens & Secrets
        if (mount("tmpfs", "/var/run/secrets", "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "size=1m") != 0) {
            throw std::runtime_error("Failed to hide /var/run/secrets directory");
        }
    }

public:
    static void enforce_limits()
    {
        apply_rlimits();
        
        // 🛡️ Hide sensitive directories using Mount Namespaces
        apply_mount_namespace();
        
        // 🛡️ Industry Standard: Prevent the process from ever gaining new privileges 
        // This explicitly neutralizes setuid binaries (like sudo) entirely.
        if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0)
        {
            throw std::runtime_error("Failed to set PR_SET_NO_NEW_PRIVS");
        }

        drop_privileges();       // Drop to sandboxuser (10002) first
        apply_seccomp_filters(); // Then lock down the syscalls
    }
};