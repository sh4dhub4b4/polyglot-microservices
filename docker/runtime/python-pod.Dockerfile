# The "Child Class" for Python
FROM polyglot-base-pod:latest

USER root

# Install Python 3 and pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*


# Set up a virtual environment by default for secure package management
RUN python3 -m venv /home/student/venv
ENV PATH="/home/student/venv/bin:$PATH"
