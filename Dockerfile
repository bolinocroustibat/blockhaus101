# Use Python 3.13 as base image
FROM python:3.13-slim
# Copy latest uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Python environment variables:
# PYTHONDONTWRITEBYTECODE=1: Prevents Python from writing .pyc files (speeds up development and reduces container size)
# PYTHONUNBUFFERED=1: Prevents Python from buffering stdout/stderr (ensures log messages are output immediately)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the project into the image
ADD . /app

# Set work directory and install dependencies in a new environment
WORKDIR /app
# Sync the project, asserting the lockfile is up to date
RUN uv sync --locked

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Port configuration:
# ARG defines the build-time PORT env var with a default value of 8000 (not available to running container)
# EXPOSE documents which port the application uses (purely informational)
ARG PORT=8000
EXPOSE ${PORT}

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]
