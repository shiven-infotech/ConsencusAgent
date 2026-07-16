# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and compiled static frontend build
COPY src/ ./src/
COPY frontend/dist/ ./frontend/dist/

# Expose port (Cloud Run sets PORT env var automatically, we expose 8080 by default)
ENV PORT=8080
EXPOSE 8080

# Run uvicorn server, binding to 0.0.0.0 and reading the port from environment variable
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
