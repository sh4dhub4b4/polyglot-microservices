# STAGE 1: Extract Engine Binary
FROM polyglot-base-pod:latest AS engine-builder

# STAGE 2: Final Runtime Image
FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libseccomp2 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r student && useradd -r -g student -m -d /home/student student
RUN groupadd -r -g 10002 sandboxuser && useradd -r -u 10002 -g 10002 -m -d /app sandboxuser

ENV HOME=/home/student
ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

COPY --from=engine-builder /usr/local/bin/engine_binary /usr/local/bin/engine_binary
RUN chmod +x /usr/local/bin/engine_binary

WORKDIR /home/student/workspace
EXPOSE 8080
CMD ["engine_binary"]
