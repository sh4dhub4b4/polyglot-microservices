# The "Child Class" for C++
# Builds upon the polyglot-base-pod
FROM polyglot-base-pod:latest

# Switch back to root temporarily to install specific C++ packages
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    cmake \
    gdb \
    && rm -rf /var/lib/apt/lists/*

# Switch back to the secure user inherited from base
