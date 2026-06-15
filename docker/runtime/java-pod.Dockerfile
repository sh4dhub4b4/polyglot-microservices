# The "Child Class" for Java / JVM
FROM polyglot-base-pod:latest

USER root

# Install OpenJDK 21
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jdk \
    maven \
    && rm -rf /var/lib/apt/lists/*

