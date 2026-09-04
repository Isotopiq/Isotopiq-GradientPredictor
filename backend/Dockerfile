FROM python:3.11-slim

# Install system deps for RDKit + XGBoost/LightGBM (libgomp1 for OpenMP)
# libxrender1 + libxext6 + libexpat1 needed for RDKit 2D depiction (rdMolDraw2D)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libfreetype6 \
    libpng16-16 \
    libxrender1 \
    libxext6 \
    libexpat1 \
    libx11-6 \
    libxau6 \
    libxdmcp6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir -e .

# Copy app code
COPY . .

# Create model storage dir
RUN mkdir -p /app/models

# Default port: 18700 (override via APP_PORT env var for Easypanel or other deployments)
ENV APP_PORT=18700
EXPOSE ${APP_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"APP_PORT\",\"18700\")}/api/v1/health')" || exit 1

# Run migrations then start the server.
# The compose file ensures db is healthy before backend starts.
# A retry loop handles transient connection issues.
# Port is configurable via APP_PORT env var (default 18700, Easypanel uses 19100).
CMD ["sh", "-c", "for i in 1 2 3 4 5; do alembic upgrade head && break || sleep 3; done && uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-18700}"]
