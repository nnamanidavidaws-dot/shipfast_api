# ─────────────────────────────────────────────
# Stage 1 — builder
# Install all dependencies into a virtual-env
# ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated venv so Stage 2 can copy just this folder
RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────
# Stage 2 — runtime  (target image < 200 MB)
# ─────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Only the runtime C lib (libpq) is needed — no compiler
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built venv from builder — nothing else

COPY --from=builder /build/venv /venv

# Fix shebang paths that point to the builder stage
RUN find /venv/bin -type f | xargs grep -l "#!/build/venv/bin/python" | \
    xargs sed -i 's|#!/build/venv/bin/python|#!/venv/bin/python3|g'

ENV PATH="/venv/bin:$PATH"

# Copy application source
COPY app/ ./app/

USER appuser

EXPOSE 8000

# ECS health-check (also used by docker-compose)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"



CMD ["/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]