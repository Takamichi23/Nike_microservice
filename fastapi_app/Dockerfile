# Stage 1: build environment
FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip and install build tools
RUN pip install --upgrade pip wheel setuptools

# Copy requirements and build wheels
COPY fastapi_app/requirements.txt ./fastapi_app/
RUN pip wheel --wheel-dir=/wheels -r fastapi_app/requirements.txt

# Copy application source
COPY fastapi_app/ ./fastapi_app/

# Stage 2: runtime image
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN useradd -m appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy and install wheels
COPY --from=builder /wheels /wheels
COPY fastapi_app/requirements.txt ./fastapi_app/
RUN pip install --no-index --find-links=/wheels -r fastapi_app/requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY --from=builder /app/fastapi_app ./fastapi_app

# Switch to non-root user
USER appuser
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run FastAPI (run from /app to allow relative imports to work)
WORKDIR /app
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
