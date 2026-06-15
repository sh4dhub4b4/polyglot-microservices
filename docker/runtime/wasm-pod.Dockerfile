# STAGE 1: Extract Engine Binary
FROM polyglot-base-pod:latest AS engine-builder

# STAGE 2: Final Runtime Image
FROM emscripten/emsdk:3.1.51

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libseccomp2 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r student && useradd -r -g student -m -d /home/student student
RUN groupadd -r -g 10002 sandboxuser && useradd -r -u 10002 -g 10002 -m -d /app sandboxuser

ENV HOME=/home/student
ENV PATH="/emsdk/upstream/emscripten:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Pre-build Emscripten system caches (libc, libc++abi, etc) so they are baked into the image.
# This prevents the engine from trying to build them at runtime (which causes 30s+ timeouts and permission errors).
RUN echo "int main() { return 0; }" > /tmp/dummy.cpp && \
    emcc /tmp/dummy.cpp -o /tmp/dummy.js -s WASM=1 -s SINGLE_FILE=1 -O3 -std=c++17 && \
    rm /tmp/dummy* && \
    chmod -R 777 /emsdk/upstream/emscripten/cache

COPY --from=engine-builder /usr/local/bin/engine_binary /usr/local/bin/engine_binary
RUN chmod +x /usr/local/bin/engine_binary

WORKDIR /home/student/workspace
EXPOSE 8080
CMD ["engine_binary"]
