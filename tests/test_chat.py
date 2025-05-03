from typing import AsyncGenerator
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from langchain_core.messages import AIMessage
from langchain_postgres import PGVectorStore
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from scaledp_chat.web.api.chat.schema import ClientMessage, Request


@pytest.fixture
def mock_vector_store() -> PGVectorStore:
    """Create a mock vector store."""
    return MagicMock(spec=PGVectorStore)


@pytest.fixture
def mock_graph_response() -> AsyncGenerator[str, None]:
    """Create a mock graph response."""

    async def mock_stream() -> AsyncGenerator[str, None]:
        yield (
            "message",
            (
                AIMessage(content="Hello! How can I help you today?"),
                {"tags": "generator"},
            ),
        )

    return mock_stream()


@pytest.fixture
def mock_build_graph(
    monkeypatch: pytest.MonkeyPatch,
    mock_graph_response: AsyncGenerator[str, None],
) -> Mock:
    """Mock the build_graph function."""
    mock_graph = Mock()
    mock_graph.astream.return_value = mock_graph_response

    def mock_build(vector_store: PGVectorStore, session: AsyncSession) -> Mock:
        return mock_graph

    monkeypatch.setattr(
        "scaledp_chat.web.api.chat.views.build_graph",
        mock_build,
    )
    return mock_graph


async def test_chat(
    fastapi_app: FastAPI,
    client_with_vector_store: AsyncClient,
    dbsession: AsyncSession,
    vector_store: PGVectorStore,
    mock_build_graph: Mock,
) -> None:
    """Test the chat endpoint."""
    url = fastapi_app.url_path_for("chat")

    # Prepare test request data
    request_data = Request(
        session_id="test-session",
        messages=[
            ClientMessage(
                role="user",
                content="Hi there!",
            ),
        ],
    )

    # Make request to the chat endpoint
    response = await client_with_vector_store.post(
        url,
        json=request_data.model_dump(),
    )

    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["x-vercel-ai-data-stream"] == "v1"

    # Check streaming response content
    response_text = ""
    async for chunk in response.aiter_text():
        response_text += chunk

    assert "Hello! How can I help you today?" in response_text


async def test_chat_invalid_request(
    fastapi_app: FastAPI,
    client_with_vector_store: AsyncClient,
) -> None:
    """Test the chat endpoint with invalid request data."""
    url = fastapi_app.url_path_for("chat")

    # Make request with invalid data
    response = await client_with_vector_store.post(
        url,
        json={},  # Empty request data should fail validation
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
