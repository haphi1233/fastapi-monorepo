"""
Common Alembic env.py template for FastAPI monorepo services.
Copy this file to your service's alembic directory and rename to env.py

Instructions:
1. Update the import path for your service's models
2. Make sure your .env file contains the required database variables
"""
from logging.config import fileConfig
import sys
import os
from dotenv import load_dotenv

# Thêm đường dẫn tới thư mục gốc của monorepo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Load environment variables from .env file
load_dotenv()

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from libs.db.base import Base

# 🔧 TODO: Import your service's models here
# Example for different services:
# from services.auth.app.models.models import User
# from services.articles.app.models.articles import Article  
# from services.user.app.models.user import User
# from services.orders.app.models.orders import Order

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 🔧 Set environment variables in config for interpolation
# These will be read from your service's .env file
config.set_main_option('DB_USERNAME', os.getenv('DB_USERNAME', 'postgres'))
config.set_main_option('DB_PASSWORD', os.getenv('DB_PASSWORD', '123456'))
config.set_main_option('DB_HOST', os.getenv('DB_HOST', 'localhost'))
config.set_main_option('DB_PORT', os.getenv('DB_PORT', '5433'))
config.set_main_option('DB_NAME', os.getenv('DB_NAME', 'defaultdb'))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
