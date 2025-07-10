# Use official Python image as base
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy package files
COPY uv.lock .
COPY pyproject.toml .

# Install Python dependencies using uv
RUN uv sync

# Copy project files
COPY .python-version .
COPY main.py .
COPY src ./src
COPY .env .

# Start the application
CMD ["uv", "run", "main.py"]
