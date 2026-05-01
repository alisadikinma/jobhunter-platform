FROM python:3.12-slim AS base

# System deps:
# - pandoc + libreoffice-core for DOCX/PDF rendering
# - postgresql-client for alembic health checks
# - curl + ca-certificates for the Claude CLI installer + health probes
# - fonts-liberation so libreoffice has something to render with
RUN apt-get update && apt-get install -y --no-install-recommends \
      pandoc \
      libreoffice-core \
      libreoffice-writer \
      postgresql-client \
      ca-certificates \
      curl \
      fonts-liberation \
      tini \
  && rm -rf /var/lib/apt/lists/*

# Claude CLI — installed via the official Node-based installer. Node is a
# transitive dep of the CLI itself; we install nodejs once and let npm grab
# the binary. `git` is needed by the plugin clone step below.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs git \
 && npm install -g @anthropic-ai/claude-code \
 && rm -rf /var/lib/apt/lists/*

# Claude plugin lives in its own repo (https://github.com/alisadikinma/jobhunter-plugin).
# Pin to a tag/branch via build arg so prod deploys are deterministic.
ARG JOBHUNTER_PLUGIN_REF=main
RUN git clone --branch "$JOBHUNTER_PLUGIN_REF" --depth 1 \
      https://github.com/alisadikinma/jobhunter-plugin.git /app/claude-plugin \
 && rm -rf /app/claude-plugin/.git

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini
COPY ./scripts ./scripts
COPY ./templates ./templates

# Generate the Pandoc reference DOCX inside the image. The file isn't
# committed (binary + locale-dependent); Pandoc's built-in default is
# single-column and ATS-safe, which is exactly what /cv-tailor needs.
RUN pandoc --print-default-data-file=reference.docx > /app/templates/cv-template.docx \
 && test -s /app/templates/cv-template.docx

RUN mkdir -p /tmp/jobhunter_agent_jobs /app/storage/cvs

# Pre-chown writable dirs to UID 1003 — matches the VPS host user
# (claudesn) so the container can share `~/.claude` OAuth credentials
# via bind mount, AND `--dangerously-skip-permissions` works for skills
# (CLI hard-rejects that flag when running as root). Fresh named volumes
# mounted on /app/storage/cvs at runtime inherit these perms.
RUN chown -R 1003:1003 /tmp/jobhunter_agent_jobs /app/storage

ENV CLAUDE_PLUGIN_PATH=/app/claude-plugin
ENV CV_STORAGE_DIR=/app/storage/cvs
ENV CV_REFERENCE_DOCX=/app/templates/cv-template.docx
ENV AGENT_JOB_LOG_DIR=/tmp/jobhunter_agent_jobs

EXPOSE 8000
ENTRYPOINT ["tini", "--"]
# Single worker: APScheduler runs in-process, so multiple workers would
# duplicate every cron-triggered scrape. docker-compose.yml override keeps
# the same worker count for prod.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
