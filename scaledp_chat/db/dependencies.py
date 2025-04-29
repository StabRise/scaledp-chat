from typing import AsyncGenerator

from langchain_postgres import PGVectorStore
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from taskiq import TaskiqDepends


async def get_db_session(
    request: Request = TaskiqDepends(),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create and get database session.

    :param request: current request.
    :yield: database session.
    """
    session: AsyncSession = request.app.state.db_session_factory()

    try:
        yield session
    finally:
        await session.commit()
        await session.close()


async def get_vector_db_session(
    request: Request,
) -> AsyncGenerator[PGVectorStore, None]:
    """
    Create and get database session.

    :param request: current request.
    :yield: database session.
    """
    yield request.app.state.vector_store
