# ─────────────────────────────────────────────
# Stage 1 — builder
# Install all dependencies into a virtual-env
# ─────────────────────────────────────────────
FROM python:3.12-alpine AS builder

WORKDIR /build

# Alpine build deps for compiling psycopg2 from source
RUN apk add --no-cache gcc musl-dev libpq-dev postgresql-dev

RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y uvloop pygments rich rich_toolkit watchfiles httptools websockets dnspython \
 && pip uninstall -y pip setuptools wheel


# ─────────────────────────────────────────────
# Stage 2 — runtime (target < 200MB)
# Alpine base is ~25MB vs ~120MB for slim
# ─────────────────────────────────────────────
FROM python:3.12-alpine AS runtime

# Non-root user for security (alpine syntax)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Only the runtime postgres C lib — no compiler
RUN apk add --no-cache libpq

# Copy the pre-built venv from builder — nothing else
COPY --from=builder /build/venv /venv

# Fix shebang paths that point to the builder stage
RUN find /venv/bin -type f | xargs grep -l "#!/build/venv/bin/python" 2>/dev/null | \
    xargs sed -i 's|#!/build/venv/bin/python|#!/venv/bin/python3|g' 2>/dev/null || true

# Strip unnecessary files from venv
RUN find /venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
 && find /venv -name "*.pyc" -delete \
 && find /venv -name "*.pyo" -delete \
 && find /venv -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true \
 && find /venv -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

ENV PATH="/venv/bin:$PATH"

# Copy application source
COPY app/ ./app/

USER appuser

EXPOSE 8000

# ECS health-check (also used by docker-compose)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]