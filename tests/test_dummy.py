import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from scaledp_chat.db.dao.dummy_dao import DummyDAO


@pytest.mark.anyio
async def test_creation(
    fastapi_app: FastAPI,
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    """Tests dummy instance creation."""
    url = fastapi_app.url_path_for("create_dummy_model")
    test_name = uuid.uuid4().hex
    response = await client.put(url, json={"name": test_name})
    assert response.status_code == status.HTTP_200_OK
    dao = DummyDAO(dbsession)

    instances = await dao.filter(name=test_name)
    assert instances[0].name == test_name


@pytest.mark.anyio
async def test_getting(
    fastapi_app: FastAPI,
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    """Tests dummy instance retrieval."""
    dao = DummyDAO(dbsession)
    test_name = uuid.uuid4().hex

    assert not await dao.filter()

    await dao.create_dummy_model(name=test_name)
    url = fastapi_app.url_path_for("get_dummy_models")
    response = await client.get(url)
    dummies = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(dummies) == 1
    assert dummies[0]["name"] == test_name
