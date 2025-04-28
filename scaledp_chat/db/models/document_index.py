import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, String, Text, Uuid

from scaledp_chat.db.base import Base
from scaledp_chat.settings import settings


class DocumentIndexModel(Base):
    """Document index model."""

    __tablename__ = "document_index"

    langchain_id: Mapped[str] = mapped_column(Uuid, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[np.array] = mapped_column(  # type: ignore
        Vector(settings.embeddings_vector_size),  # type: ignore
    )
    document_id: Mapped[str] = mapped_column(Uuid)
    langchain_metadata: Mapped[JSON] = mapped_column(JSON)


class DocumentFileModel(Base):
    """Document file model."""

    __tablename__ = "document_file"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    filepath: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    file_metadata: Mapped[dict[str, str]] = mapped_column(JSON)
