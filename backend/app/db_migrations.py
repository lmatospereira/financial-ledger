"""Database migration runner with retrofit support for pre-Alembic databases.

This module handles running Alembic migrations at startup with special handling
for existing production/dev databases that predate the migration system.

Retrofit logic: If the database already has app tables (e.g., `accounts`) but
no `alembic_version` table, this means it's one of our pre-Alembic production
databases that will already be at the correct schema (we've manually patched
them with ALTER TABLE in the meantime). In this case, we call `stamp head`
instead of `upgrade head` to mark the DB as being at the baseline migration
without trying to re-run CREATE TABLE commands on tables that already exist.
"""
import logging
from sqlalchemy import inspect

from alembic.config import Config
from alembic.command import stamp, upgrade

from app.database import DATABASE_URL, engine

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run Alembic migrations with retrofit support for pre-Alembic databases.

    If the database has app tables but no alembic_version table yet, we stamp
    the current head revision instead of upgrading — this is the retrofit path
    for existing production/dev databases.
    """
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

    # Check if alembic_version table exists and if app tables exist.
    inspector = inspect(engine)
    has_alembic_version = "alembic_version" in inspector.get_table_names()
    has_app_tables = "accounts" in inspector.get_table_names()

    if not has_alembic_version and has_app_tables:
        # This is a retrofit case: pre-Alembic database with existing tables.
        # Mark it as being at the current head without re-running migrations.
        logger.info(
            "Database already has app tables but no alembic_version table. "
            "Stamping as at baseline migration (retrofit for pre-Alembic DB)."
        )
        stamp(config, "head")
    else:
        # Normal case: fresh DB or already-migrated DB. Run migrations.
        logger.info("Running Alembic migrations.")
        upgrade(config, "head")
