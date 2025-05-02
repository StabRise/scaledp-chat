from functools import partial
from typing import Annotated, Any, Dict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_postgres import PGVectorStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.graph.message import add_messages
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import List, TypedDict

from scaledp_chat.db.models.document_index import DocumentFileModel
from scaledp_chat.web.api.chat.llm import generator_llm, retrieve_llm
from scaledp_chat.web.api.chat.prompts import defenition_prompt, rag_prompt


class State(TypedDict):
    """Represents the state of a conversation."""

    messages: Annotated[list[BaseMessage], add_messages]
    context: List[Document]
    answer: str


async def retrieve(
    state: State,
    vector_store: PGVectorStore,
) -> Dict[str, List[Document]]:
    """
    Retrieve relevant documents based on the user's question using semantic search.

    Args:
        state (State): The current conversation state containing:
            - messages (List[BaseMessage]): Conversation history
            - context (List[Document]): Previously retrieved documents
            - answer (str): Last generated response
        vector_store (PGVectorStore): PostgreSQL vector store for semantic search

    Returns:
        Dict[str, List[Document]]: Dictionary with key "context" containing the most
            relevant documents for the query

    The function:
    1. Extracts the latest user question from conversation history
    2. Uses LLM to extract key terms and concepts from the question
    3. Augments search terms with common system keywords
    4. Performs semantic similarity search to find relevant documents
    5. Returns top matching documents as context for answer generation

    Notes:
        - Uses defenition_prompt to extract search terms from question
        - Adds system-specific keywords to improve document retrieval
        - Returns top 10 most semantically similar documents
    """
    # Get latest question from conversation
    question: str = state["messages"][-1].content[0]["text"]  # type: ignore

    # Extract key terms using LLM
    messages = defenition_prompt.invoke({"question": question})
    response = retrieve_llm.invoke(messages.to_messages())

    # Add system keywords to search terms
    defenitions = response.content[0] + (  # type: ignore
        ", ScaleDPSession, DataToImage, show_image,how_text"
    )

    # Perform semantic search
    retrieved_docs: List[Document] = await vector_store.asimilarity_search(
        defenitions,
        k=10,
    )

    return {"context": retrieved_docs}


async def generate(state: State, db_session: AsyncSession) -> Dict[str, Any]:
    """
    Generate a response based on the context and user's question
    using RAG (Retrieval-Augmented Generation).

    Args:
        state (State): A TypedDict containing:
            - messages: List of conversation messages
            - context: List of retrieved Documents
            - answer: Generated response string
        db_session (AsyncSession): SQLAlchemy async database session

    Returns:
        Dict[str, str]: Dictionary with key "answer" containing the generated response

    The function performs these steps:
    1. Retrieves full document contents from the database for each context document
       using the provided async session
    2. Combines all document contents into a single string separated by newlines
    3. Extracts the latest question from the conversation messages
    4. Formats the prompt with question and context using rag_prompt
    5. Generates a response using the LLM with the complete conversation history

    Notes:
        - Expects document file_ids to be stored in the Document metadata
        - Uses the rag_prompt template for formatting the context and question
        - Preserves conversation history when generating the response
    """

    # Fetch full document contents from database
    file_contents: List[str] = []
    ##async with async_session() as session:
    for doc in state["context"]:
        document_file: DocumentFileModel | None = await db_session.get(
            DocumentFileModel,
            doc.metadata["file_id"],
        )
        if document_file:
            file_contents.append(document_file.content)

    # Combine all document contents
    docs_content = "\n\n".join(file_contents)

    # Extract the latest question from messages
    question = state["messages"][-1].content[0]["text"]  # type: ignore

    # Format the prompt with question and context
    messages = rag_prompt.invoke({"question": question, "context": docs_content})

    # Generate response using the LLM
    response = await generator_llm.ainvoke(state["messages"] + messages.to_messages())

    return {"answer": response.content}


def build_graph(vector_store: PGVectorStore, db_session: AsyncSession) -> CompiledGraph:
    """Build a state graph for the RAG application."""

    partial_retrieve = partial(retrieve, vector_store=vector_store)
    partial_generate = partial(generate, db_session=db_session)

    graph_builder = StateGraph(State).add_sequence(
        [("retrieve", partial_retrieve), ("generate", partial_generate)],
    )
    graph_builder.add_edge(START, "retrieve")

    return graph_builder.compile(checkpointer=MemorySaver())
