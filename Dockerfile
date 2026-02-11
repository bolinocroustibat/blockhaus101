# Use official uv image with Python 3.14 with uv preinstalled
# (alpine is smaller, but longer to build and less compatible with setuptools-scm)
# https://docs.astral.sh/uv/guides/integration/docker/
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

# Python environment variables:
# PYTHONDONTWRITEBYTECODE=1: Prevents Python from writing .pyc files (speeds up development and reduces container size)
# PYTHONUNBUFFERED=1: Prevents Python from buffering stdout/stderr (ensures log messages are output immediately)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the project into the image
ADD . /app

# Set work directory
WORKDIR /app

# Install cron for scheduled tasks
RUN apt-get update && apt-get install -y --no-install-recommends cron && rm -rf /var/lib/apt/lists/*

# Accept version from CI build-arg so setuptools-scm doesn't need git at build time
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# Sync the project, asserting the lockfile is up to date
RUN uv sync --locked

RUN chmod +x /app/cron/entrypoint.sh

# Document that the container listens on internal port 8000
EXPOSE 8000

# Run migrations, collect static files, and start the server
CMD uv run manage.py migrate && \
    uv run manage.py collectstatic --noinput && \
    exec uv run gunicorn blockhaus101.asgi:application -w 4 -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:8000"
