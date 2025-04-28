import logging
import os
from langchain_community.document_loaders import GitLoader


from scaledp_chat.db.dao.document_file_dao import DocumentFileDAO
from scaledp_chat.db.models.document_index import DocumentIndexModel
from scaledp_chat.settings import settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGEngine, PGVectorStore
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import asyncio

from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


async def main():

    logging.info(f"Clone git repo: {settings.repo_url}")
    absolute_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "repos", "scaledp")
    )
    loader = GitLoader(
        repo_path=absolute_path,
        clone_url=settings.repo_url,
        file_filter=lambda file_path: file_path.endswith(".py"),
        branch="master",
    )
    data = loader.load()

    logging.info(len(data))

    contents = []
    metadatas = []

    engine = create_async_engine(str(settings.db_url), echo=settings.db_echo)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        try:
            dao = DocumentFileDAO(session)

            logging.info(f"Processing {len(data)} files")
            for index, file_data in enumerate(data):
                try:
                    logging.info(f"Processing file {index + 1}/{len(data)}")
                    logging.info(f"File metadata: {file_data.metadata}")
                    file_id = await dao.create(
                        content=file_data.page_content,
                        filepath=file_data.metadata["file_path"],
                        file_type=file_data.metadata["file_type"],
                        file_metadata=file_data.metadata,
                    )

                    if not file_id:
                        logging.error(
                            f"Failed to create file record: {file_data.metadata['file_path']}"
                        )
                        continue

                    logging.info(f"Created file record with ID: {file_id}")

                    metadata = (
                        file_data.metadata.copy()
                    )  # Create a copy to avoid modifying the original
                    metadata["file_id"] = file_id
                    contents.append(file_data.page_content)
                    metadatas.append(metadata)

                except Exception as e:
                    logging.error(
                        f"Error processing file {file_data.metadata.get('file_path')}: {str(e)}"
                    )
                    continue

            # Commit the transaction
            await session.commit()

            logging.info(f"Successfully processed {len(contents)} files")
            logging.info(f"Contents length: {len(contents)}")
            logging.info(f"Metadatas length: {len(metadatas)}")

        except Exception as e:
            logging.error(f"Database transaction failed: {str(e)}")
            await session.rollback()
            raise

    python_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON, chunk_size=50, chunk_overlap=10, add_start_index=True
    )

    python_docs = python_splitter.create_documents(contents, metadatas=metadatas)

    logging.info(f"Number of the chunks:{len(python_docs)}")

    embeddings = HuggingFaceEmbeddings(model_name=settings.embeddings_model)

    engine = PGEngine.from_engine(engine)

    vector_store = await PGVectorStore.create(
        engine=engine,
        table_name=DocumentIndexModel.__tablename__,
        embedding_service=embeddings,
    )

    ids = await vector_store.aadd_documents(documents=python_docs)
    logging.info(f"Number of the chunks:{len(ids)}")


if __name__ == "__main__":
    asyncio.run(main())
