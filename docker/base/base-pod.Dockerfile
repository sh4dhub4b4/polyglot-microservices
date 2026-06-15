# 1. Base Pod Dockerfile (The "Parent Class")
# All language-specific pods will inherit from this base image to share setup logic.

# ==========================================
# STAGE 1: Shared Builder (Built ONLY ONCE!)
# ==========================================
FROM ubuntu:22.04 AS builder

# Combine RUN commands and clean apt cache in same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    g++ \
    gcc \
    libseccomp-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY src/cpp-processing-engine/src/ ./src/

# Compile the hypervisor/engine binary
RUN g++ -O3 -flto -std=c++17 \
    src/main.cpp -o engine_binary \
    -pthread -lseccomp \
    && strip engine_binary

# ==========================================
# STAGE 2: Base Runtime Image
# ==========================================
FROM ubuntu:22.04

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Update and install common base utilities required by all pods
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    git \
    build-essential \
    libseccomp2 \
    && rm -rf /var/lib/apt/lists/*

# Set up the secure runner user (Shared across all pods)
RUN groupadd -r student && useradd -r -g student -m -d /home/student student

# Set strict limits via Docker/K8s (no root allowed)
ENV HOME=/home/student
ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /home/student/workspace

# Copy the engine binary from the builder stage
COPY --from=builder /build/engine_binary /usr/local/bin/engine_binary
RUN chmod +x /usr/local/bin/engine_binary

# Switch to the secure user
# IMPORTANT: The execution engine runs as root to use libseccomp, but drops privileges internally
# We must NOT use `USER student` in the Dockerfile because the engine_binary requires root to setup seccomp
# The engine_binary internally drops to 'sandboxuser' (or 'student' in our case) before executing code
# Wait, engine_binary.cpp expects 'sandboxuser' uid/gid!
RUN groupadd -r -g 10002 sandboxuser && \
    useradd -r -u 10002 -g 10002 -m -d /app sandboxuser

EXPOSE 8080
CMD ["engine_binary"]
