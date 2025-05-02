from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scaledp_chat.services.rabbit.lifespan import init_rabbit, shutdown_rabbit
from scaledp_chat.settings import settings
from scaledp_chat.tkq import broker


def _setup_db(app: FastAPI) -> None:  # pragma: no cover
    """
    Creates connection to the database.

    This function creates SQLAlchemy engine instance,
    session_factory for creating sessions
    and stores them in the application's state property.

    :param app: fastAPI application.
    """
    engine = create_async_engine(str(settings.db_url), echo=settings.db_echo)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory


def _setup_vector_store(app: FastAPI) -> None:
    from scaledp_chat.web.api.chat.vector_store import get_vector_store

    app.state.vector_store = get_vector_store()


@asynccontextmanager
async def lifespan_setup(
    app: FastAPI,
) -> AsyncGenerator[None, None]:  # pragma: no cover
    """
    Actions to run on application startup.

    This function uses fastAPI app to store data
    in the state, such as db_engine.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """

    app.middleware_stack = None
    if settings.with_taskiq and not broker.is_worker_process:
        await broker.startup()
    _setup_db(app)
    _setup_vector_store(app)
    if settings.with_taskiq:
        init_rabbit(app)
    app.middleware_stack = app.build_middleware_stack()

    yield
    if not broker.is_worker_process:
        await broker.shutdown()
    await app.state.db_engine.dispose()

    await shutdown_rabbit(app)
