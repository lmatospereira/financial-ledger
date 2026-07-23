"""SQLAlchemy engine/session setup.

The SQLite file path is configurable via the DATABASE_URL env var and
defaults to ./data/livro_caixa.db (relative to the backend/ working dir).
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_DB_PATH = Path("./data/livro_caixa.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Ensure the parent directory for file-based sqlite DBs exists.
if DATABASE_URL.startswith("sqlite:///") and DATABASE_URL != "sqlite:///:memory:":
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    if db_file:
        parent = Path(db_file).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
