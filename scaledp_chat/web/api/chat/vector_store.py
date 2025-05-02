from typing import Optional

from langchain_postgres import PGEngine, PGVectorStore
from langchain_together import TogetherEmbeddings
from sqlalchemy.ext.asyncio import AsyncEngine

from scaledp_chat.db.models.document_index import DocumentIndexModel
from scaledp_chat.settings import settings


def get_vector_store(pg_engine: Optional[AsyncEngine] = None) -> PGVectorStore:
    """
    Creates and returns a Postgres vector store for document embeddings.

    Returns:
        PGVectorStore: A Postgres vector store instance configured with:
            - HuggingFace embeddings model from settings
            - Database connection from settings
            - Document index table name from DocumentIndexModel
    """

    embeddings = TogetherEmbeddings(
        model=settings.togetherai_embeddings_model,
        api_key=settings.togetherai_embeddings_api_key,
    )

    if pg_engine is None:
        engine = PGEngine.from_connection_string(str(settings.db_url))
    else:
        engine = PGEngine.from_engine(pg_engine)

    return PGVectorStore.create_sync(
        engine=engine,
        table_name=DocumentIndexModel.__tablename__,
        embedding_service=embeddings,
    )


async def aget_vector_store(pg_engine: Optional[AsyncEngine] = None) -> PGVectorStore:
    """
    Asynchronously creates and returns a Postgres vector store for document embeddings.

    Args:
        pg_engine: Optional SQLAlchemy AsyncEngine instance. If not provided,
                  will create engine from connection string in settings.

    Returns:
        PGVectorStore: A Postgres vector store instance configured with:
            - HuggingFace embeddings model from settings
            - Database connection from settings or provided engine
            - Document index table name from DocumentIndexModel
    """

    embeddings = TogetherEmbeddings(
        model=settings.togetherai_embeddings_model,
        api_key=settings.togetherai_embeddings_api_key,
    )

    if pg_engine is None:
        engine = PGEngine.from_connection_string(str(settings.db_url))
    else:
        engine = PGEngine.from_engine(pg_engine)

    return await PGVectorStore.create(
        engine=engine,
        table_name=DocumentIndexModel.__tablename__,
        embedding_service=embeddings,
    )
