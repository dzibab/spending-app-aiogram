# Use official Python image as base
FROM python:3.12-slim

# Copy uv binary from multi-stage build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy only dependency files first for better layer caching
COPY uv.lock pyproject.toml ./

# Install Python dependencies using uv
RUN uv sync --no-cache

# Copy only necessary project files
COPY main.py ./
COPY src ./src

# Optionally copy .env and .python-version if needed at runtime
COPY .env .python-version ./

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Start the application
CMD ["uv", "run", "main.py"]
