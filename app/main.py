import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Product
from app.schemas import ProductCreate, ProductResponse
from app.routers import products

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Secrets Manager helper ────────────────────────────────────────────────────
def get_db_url_from_secrets_manager() -> str:
    """
    Fetch DB credentials from AWS Secrets Manager.
    Falls back to DATABASE_URL env var for local development.
    """
    secret_name = os.getenv("DB_SECRET_NAME")

    if not secret_name:
        # Local dev: just read a plain DATABASE_URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError(
                "Set either DB_SECRET_NAME (production) or DATABASE_URL (local dev)"
            )
        logger.info("Using DATABASE_URL from environment (local dev mode)")
        return db_url

    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        host = secret["host"]
        port = secret.get("port", 5432)
        dbname = secret["dbname"]
        username = secret["username"]
        password = secret["password"]
        url = f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
        logger.info("DB credentials loaded from Secrets Manager: %s", secret_name)
        return url
    except ClientError as exc:
        logger.error("Failed to retrieve secret '%s': %s", secret_name, exc)
        raise


# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup: resolve DB URL → create tables."""
    logger.info("Starting ShipFast Product Catalogue API …")

    db_url = get_db_url_from_secrets_manager()

    # Patch the engine with the resolved URL
    from app import database as db_module
    db_module._engine = create_engine(db_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=db_module._engine, checkfirst=True)

    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down.")


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="ShipFast Product Catalogue API",
    description="Production-ready product catalogue service.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(products.router, prefix="/products", tags=["products"])


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health_check():
    """
    ECS / ALB health check target.
    Returns 200 when the app is running and the DB is reachable.
    """
    from app.database import get_engine

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(exc)})