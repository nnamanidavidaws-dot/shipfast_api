"""
database.py — SQLAlchemy engine + session factory.

The real engine is injected at startup by main.py after credentials
are fetched from Secrets Manager. A placeholder engine pointing at
a dummy URL is created here so that imports never fail.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Placeholder — replaced at startup in main.py lifespan
_engine = create_engine(
    "postgresql://placeholder:placeholder@localhost/placeholder",
    pool_pre_ping=True,
)

Base = declarative_base()

# SessionLocal is a factory; it always uses the current _engine
def _make_session():
    return sessionmaker(autocommit=False, autoflush=False, bind=_engine)()


def get_engine():
    return _engine


def get_db():
    """FastAPI dependency — yields a DB session, closes it when done."""
    db = _make_session()
    try:
        yield db
    finally:
        db.close()


# Alias used by main.py
engine = _engine