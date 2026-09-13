# Stage 1: Dependency builder
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .

# Install torch CPU-only FIRST to prevent CUDA wheels
RUN pip install --no-cache-dir --user --default-timeout=120 --retries 5 \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --user --default-timeout=120 --retries 5 -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . /app

EXPOSE 8000

# Lightweight health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD python -c "import sys; print('ok')" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
