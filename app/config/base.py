from asyncio import current_task
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from beanie import init_beanie
from dependency_injector import containers, providers
from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from tortoise import Tortoise

from app.utils.logger import get_logger
from settings import config as app_config

logger = get_logger()


class MeepoMongo:
    def __init__(self):
        self._main: Optional[AgnosticClient] = None

    def init(self, mongo_config: dict) -> None:
        self._main = AsyncIOMotorClient(**mongo_config.get("main", {}))

    @property
    def main(self) -> AgnosticClient:
        assert self._main is not None
        return self._main


class MeepoRedis:
    def __init__(self):
        self._main: Optional[Redis] = None

    def init(self, redis_config: dict) -> None:
        self._main = Redis(**redis_config.get("main", {}))

    @property
    def main(self) -> Redis:
        assert self._main is not None
        return self._main


class MeepoMysql:
    def __init__(self):
        self._main: Optional[AsyncEngine] = None
        self._tortoise_config: Optional[dict] = None

    def init(self, mysql_config: dict) -> None:
        self._main = create_async_engine(**mysql_config.get("main", {}))
        self._tortoise_config = mysql_config.get("tortoise", {})

    def session_factory(self, engine_name: str = "main") -> async_scoped_session:
        return async_scoped_session(
            async_sessionmaker(
                class_=AsyncSession,
                bind=getattr(self, engine_name),
                expire_on_commit=False,
            ),
            scopefunc=current_task,
        )

    @property
    def main(self) -> AsyncEngine:
        assert self._main is not None
        return self._main

    @property
    def tortoise(self):
        return self._tortoise_config

    @asynccontextmanager
    async def main_session(self) -> AsyncIterator[AsyncSession]:
        session = self.session_factory()()
        try:
            yield session
        except Exception as e:
            logger.error(e)
            await session.rollback()
        finally:
            await session.close()


def create_mongo_connect_once(mongo_config: dict) -> MeepoMongo:
    mongo = MeepoMongo()
    mongo.init(mongo_config)

    return mongo


def create_redis_connect_once(redis_config: dict) -> MeepoRedis:
    redis = MeepoRedis()
    redis.init(redis_config)

    return redis


def create_mysql_connect_once(mysql_config: dict) -> MeepoMysql:
    mysql = MeepoMysql()
    mysql.init(mysql_config)

    return mysql


class Container(containers.DeclarativeContainer):
    __self__ = providers.Self()
    config = providers.Configuration()
    config.from_dict(app_config)

    mongo = providers.Singleton(create_mongo_connect_once, config.get("db").get("mongo", {}))
    redis = providers.Singleton(create_redis_connect_once, config.get("db").get("redis", {}))
    mysql = providers.Singleton(create_mysql_connect_once, config.get("db").get("mysql", {}))

    init_odm_model = providers.Callable(init_beanie)
    init_rdm_model = providers.Callable(Tortoise.init)
    generate_schemas = providers.Callable(Tortoise.generate_schemas)
