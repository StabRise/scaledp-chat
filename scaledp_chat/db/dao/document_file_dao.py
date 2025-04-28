import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from scaledp_chat.db.dependencies import get_db_session
from scaledp_chat.db.models.document_index import DocumentFileModel


class DocumentFileDAO:
    """Class for accessing dummy table."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def create(
        self,
        content: str,
        filepath: str,
        file_type: str,
        file_metadata: dict[str, str],
    ) -> str:
        """
        Add single DocumentFileModel to session.

        Args:
            content: The content of the document file
            filepath: The path to the document file
            file_type: The type of the document file
            file_metadata: Additional metadata about the file as key-value pairs

        Returns:
            str: The ID of the created document file record
        """
        id = str(uuid.uuid4())
        self.session.add(
            DocumentFileModel(
                id=id,
                content=content,
                filepath=filepath,
                file_type=file_type,
                file_metadata=file_metadata,
            ),
        )
        return id
