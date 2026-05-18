# syntax=docker/dockerfile:1.4
FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Fix Microsoft base image GPG error by removing the broken Yarn repo
RUN rm -f /etc/apt/sources.list.d/yarn.list

# Install comprehensive dev tools (C++, Java, Arduino)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake gdb git curl openjdk-17-jdk maven \
    && rm -rf /var/lib/apt/lists/*

# Install Arduino CLI
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh

# Setup Python Dev Environment via uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
RUN uv pip install --system jupyter debugpy

WORKDIR /workspace
CMD ["sleep", "infinity"]