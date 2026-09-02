"""Database configuration for PostgreSQL-backed durable task state."""

from collections.abc import Iterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EIW_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://eiw:eiw@localhost:5432/eiw"


def create_database_engine(settings: DatabaseSettings | None = None) -> Engine:
    resolved = settings or DatabaseSettings()
    return create_engine(resolved.database_url, pool_pre_ping=True)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
