import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_postgres import PGVectorStore
from sqlalchemy.ext.asyncio import AsyncSession

from scaledp_chat.db.dependencies import get_db_session, get_vector_db_session

from .graph import State, build_graph
from .schema import Request
from .utils import convert_to_langgraph_messages

router = APIRouter()


@router.post("/")
async def chat(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    vector_store: PGVectorStore = Depends(get_vector_db_session),
) -> StreamingResponse:
    """
    Handle chat requests by streaming AI responses.

    Args:
        request (Request): The incoming chat request containing messages
        and session information.

    Returns:
        StreamingResponse: A streaming response containing the AI's generated messages.

    The function:
    1. Sets up configuration for the chat session
    2. Converts incoming messages to the LangGraph format
    3. Streams responses from the graph with a slight delay between messages
    4. Returns a properly formatted event stream
    """

    # Configure the chat session with user and thread identification
    config = RunnableConfig(
        configurable={
            "thread_id": "{user_id}-{request.session_id}",
            "user_id": "user_id",
        },
    )

    # Convert incoming messages to LangGraph format
    messages: list[BaseMessage] = convert_to_langgraph_messages(request.messages)

    # Build the graph for processing messages with the given vector store and db session
    graph = build_graph(vector_store, session)

    async def stream_graph_events(
        messages: list[BaseMessage],
    ) -> AsyncGenerator[str, None]:
        """
        Generate a stream of events from the graph.

        Args:
            messages (list[BaseMessage]): List of messages to process.

        Yields:
            str: Formatted JSON strings containing the AI's responses.
        """
        async for stream_mode, chunk in graph.astream(
            {"messages": messages},
            config=config,
            stream_mode=["updates", "messages"],
        ):
            if stream_mode == "updates":
                updates: dict[str, State] = chunk  # type: ignore
                # Handle updates
                if "retrieve" in updates and "context" in updates["retrieve"]:
                    context = [item.metadata for item in updates["retrieve"]["context"]]
                    for item in context[0:10]:
                        yield (
                            f'h:{{"sourceType": "url", "id": "'
                            f'{item['start_index']}",'
                            f' "url": "{item['source']}", "title": "'
                            f'{item['source']}"}}\n'
                        )
            else:
                # Handle messages
                event, metadata = chunk  # type: ignore
                if "generator" in metadata.get("tags", []):  # type: ignore
                    yield "0:{text}\n".format(text=json.dumps(event.content))  # type: ignore

    # Create and configure the streaming response
    response: StreamingResponse = StreamingResponse(
        stream_graph_events(messages),
        media_type="text/event-stream",
    )
    # Add Vercel AI compatibility header
    response.headers["x-vercel-ai-data-stream"] = "v1"
    return response
