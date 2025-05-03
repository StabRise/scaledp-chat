import logging
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
    Retrieve relevant documents using semantic search based on user queries
     and extracted concepts.
    Args:
        state (State): The current conversation state containing:
            - messages (List[BaseMessage]): The complete conversation history
            - context (List[Document]): Previously retrieved reference documents
            - answer (str): The last generated response
        vector_store (PGVectorStore): Vector database instance for semantic
         document search

    Returns:
        Dict[str, List[Document]]: Dictionary containing retrieved documents
        under "context" key, with documents sorted by relevance and deduplicated by
        source

    Process Flow:
    1. Extracts the most recent user question from the conversation
    2. Uses an LLM to analyze the question and extract relevant search terms
    3. Combines extracted terms with predefined system keywords
    4. Performs semantic similarity search for each search term
    5. Deduplicates results based on document sources
    6. Returns unique, relevant documents as context

    Implementation Details:
    - Utilizes defenition_prompt to extract meaningful search terms
    - Includes system-specific keywords (ScaleDPSession, DataToImage, show_image)
    - Performs incremental searches with both extracted and predefined terms
    - Maintains result uniqueness by tracking document sources
    - Prioritizes more recent/relevant search terms in the search order
    """
    # Extract the latest user question from the conversation history
    question: str = state["messages"][-1].content[0]["text"]  # type: ignore

    # Use LLM to analyze and extract key concepts from the question
    messages = defenition_prompt.invoke({"question": question})
    response = retrieve_llm.invoke(messages.to_messages())

    # Define core system keywords and combine with extracted terms
    predefined_context = ["ScaleDPSession", "DataToImage", "show_image"]
    defenitions = response.content.split(",")  # type: ignore

    # Log extracted terms for debugging and monitoring
    logging.info(f"Extracted defenitions: {defenitions}")

    # Combine all search terms if definitions were successfully extracted
    if defenitions:
        predefined_context.extend(defenitions)

    # Include the original question in the search terms
    predefined_context.append(question)

    # Initialize collections for document retrieval
    retrieved_docs = []
    seen_sources = set()

    # Perform semantic search for each term, starting with most specific
    for context in predefined_context[::-1]:
        docs = await vector_store.asimilarity_search(
            context,
            k=3,  # Retrieve top 3 matches per term
        )
        # Deduplicate documents based on source
        for doc in docs:
            if doc.metadata["source"] not in seen_sources:
                retrieved_docs.append(doc)
                seen_sources.add(doc.metadata["source"])

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
