FROM python:3.12-slim

WORKDIR /app

# Install system deps needed by some packages (grpcio, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache — only rebuilds on requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package and its data
COPY backend/ ./backend/

# /app/backend/data and /app/backend/config are part of the image by default.
# Mount a volume over them in production to persist writes (pending_approvals, etc.)
VOLUME ["/app/backend/data"]

EXPOSE 8000

# Run as non-root
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
