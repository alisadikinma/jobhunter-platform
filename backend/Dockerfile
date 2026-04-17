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
# the binary.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @anthropic-ai/claude-code \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini
COPY ./scripts ./scripts
COPY ./templates ./templates

RUN mkdir -p /tmp/jobhunter_agent_jobs /app/storage/cvs

# Claude plugin dir is mounted from the host at runtime (docker-compose).
ENV CLAUDE_PLUGIN_PATH=/app/claude-plugin
ENV CV_STORAGE_DIR=/app/storage/cvs
ENV AGENT_JOB_LOG_DIR=/tmp/jobhunter_agent_jobs

EXPOSE 8000
ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
