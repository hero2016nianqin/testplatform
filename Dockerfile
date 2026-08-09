# ============================================================
# Test Platform — Production Docker Image
# ============================================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ── Install system dependencies ────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies ────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ───────────────────────────────────
COPY . .

# ── Create runtime directories ─────────────────────────────
RUN mkdir -p uploads logs database

# ── Expose port ────────────────────────────────────────────
EXPOSE 5000

# ── Default: run with Gunicorn + eventlet ──────────────────
CMD ["gunicorn", "-k", "eventlet", "-w", "8", "-b", "0.0.0.0:5000", \
     "--worker-connections", "2000", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "run:app"]
