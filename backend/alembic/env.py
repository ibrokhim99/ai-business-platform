from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from urllib.parse import quote_plus

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override with env vars if available. Docker Compose passes POSTGRES_* to the
# backend container, while alembic.ini contains only local fallback defaults.
db_url = os.environ.get("DATABASE_URL_SYNC")
if not db_url and os.environ.get("POSTGRES_HOST"):
    user = quote_plus(os.environ.get("POSTGRES_USER", "aibp"))
    password = quote_plus(os.environ.get("POSTGRES_PASSWORD", "changeme"))
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "aibp")
    db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
if not db_url:
    db_url = config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", db_url)

# Import ORM models so Alembic can detect schema changes
try:
    from app.db.base import Base
    from app.models import user, audit, model_registry, business  # noqa: F401
    target_metadata = Base.metadata
except ImportError:
    target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
