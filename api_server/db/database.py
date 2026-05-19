from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

POOL_SIZE = 20
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600


@dataclass
class DatabaseConfig:
    url: str
    pool_size: int = POOL_SIZE
    max_overflow: int = MAX_OVERFLOW
    pool_timeout: int = POOL_TIMEOUT
    pool_recycle: int = POOL_RECYCLE
    echo: bool = False
    mysql_charset: str = "utf8mb4"
    mysql_collation: str = "utf8mb4_unicode_ci"


def create_postgres_config(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    **kwargs,
) -> DatabaseConfig:
    url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
    return DatabaseConfig(url=url, **kwargs)


def create_mysql_config(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    charset: str = "utf8mb4",
    collation: str = "utf8mb4_unicode_ci",
    **kwargs,
) -> DatabaseConfig:
    url = f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}?charset={charset}&collation={collation}"
    kwargs.setdefault("mysql_charset", charset)
    kwargs.setdefault("mysql_collation", collation)
    return DatabaseConfig(url=url, **kwargs)


def create_sqlite_config(database: str, **kwargs) -> DatabaseConfig:
    url = f"sqlite+aiosqlite:///{database}"
    return DatabaseConfig(url=url, **kwargs)


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _engine: Optional[AsyncEngine] = None

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._engine: Optional[AsyncEngine] = None

    @classmethod
    def init(cls, config: DatabaseConfig) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def create_engine(self) -> AsyncEngine:
        driver = self._config.url.split("+")[0] if "+" in self._config.url else self._config.url.split("://")[0]
        if driver == "postgresql":
            pool_args = {
                "pool_size": self._config.pool_size,
                "max_overflow": self._config.max_overflow,
                "pool_timeout": self._config.pool_timeout,
                "pool_recycle": self._config.pool_recycle,
            }
        elif driver == "mysql":
            pool_args = {
                "pool_size": self._config.pool_size,
                "max_overflow": self._config.max_overflow,
                "pool_timeout": self._config.pool_timeout,
                "pool_recycle": self._config.pool_recycle,
            }
        else:
            pool_args = {}
        
        self._engine = create_async_engine(
            self._config.url,
            echo=self._config.echo,
            **pool_args,
        )
        return self._engine

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("DatabaseManager not initialized. Call create_engine() first.")
        return self._engine

    def close(self) -> None:
        if self._engine is not None:
            import asyncio
            asyncio.run(self._engine.dispose())
            self._engine = None
            DatabaseManager._instance = None
            DatabaseManager._engine = None


def get_engine(config: DatabaseConfig) -> AsyncEngine:
    manager = DatabaseManager(config)
    return manager.create_engine()