FROM python:3.10-slim

# System dependencies (needed for psycopg2, curl for healthcheck)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project files
COPY backend /app/backend
COPY worker /app/worker
COPY bot /app/bot
COPY Frontend /app/Frontend
COPY alembic.ini /app/alembic.ini

# Python path
ENV PYTHONPATH=/app

# Default command (overridden by docker-compose for backend)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
