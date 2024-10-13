import json
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app  # Assuming your FastAPI app is in app.py


@pytest.fixture(scope="module", autouse=True)
def mock_call_llm():
    with patch("src.service.ApplicationService._call_llm", new_callable=AsyncMock) as mock_method:

        # Create a mock response object with a 'choices' attribute
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({"output_key": "mocked_output"})))]

        mock_method.return_value = mock_response
        yield


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    async with ASGITransport(app=app) as transport:
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            yield client


@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_create_application(client):
    request_data = {
        "prompt_config": "Test prompt",
        "input_schema": {},
        "output_schema": {},
    }
    response = await client.post("/applications", json=request_data)
    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data


@pytest.mark.anyio
async def test_create_application_invalid_schema(client):
    request_data = {
        "prompt_config": "Test prompt",
        "input_schema": {
            "type": "object",
            "properties": {"input_key": {"type": "invalid_type"}},  # invalid type
            "required": ["input_key"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"output_key": {"type": "string"}},
            "required": ["output_key"],
        },
    }
    response = await client.post("/applications", json=request_data)
    assert response.status_code == 400
    assert "Schema validation error" in response.json()["detail"]


@pytest.mark.anyio
async def test_generate_completion(client):
    # First, create an application
    request_data = {
        "prompt_config": "Test prompt",
        "input_schema": {"type": "object", "properties": {"input_key": {"type": "string"}}, "required": ["input_key"]},
        "output_schema": {
            "type": "object",
            "properties": {"output_key": {"type": "string"}},
            "required": ["output_key"],
        },
    }
    response = await client.post("/applications", json=request_data)
    assert response.status_code == 200
    application_id = response.json()["id"]

    # Now, generate a completion
    inference_request = {"input_data": {"input_key": "test input"}}
    response = await client.post(f"/applications/{application_id}/completions", json=inference_request)
    print(response.json())
    assert response.status_code == 200
    response_data = response.json()
    assert "output_data" in response_data
    assert response_data["output_data"] == {"output_key": "mocked_output"}


@pytest.mark.anyio
async def test_generate_completion_invalid_input(client):
    # First, create an application
    request_data = {
        "prompt_config": "Test prompt",
        "input_schema": {"type": "object", "properties": {"input_key": {"type": "string"}}, "required": ["input_key"]},
        "output_schema": {
            "type": "object",
            "properties": {"output_key": {"type": "string"}},
            "required": ["output_key"],
        },
    }
    response = await client.post("/applications", json=request_data)
    assert response.status_code == 200
    application_id = response.json()["id"]

    # Now, generate a completion with invalid input
    inference_request = {"input_data": {"input_key": 123}}  # Invalid type, should be string
    response = await client.post(f"/applications/{application_id}/completions", json=inference_request)
    assert response.status_code == 400
    assert "Input validation failed" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_application(client):
    # First, create an application
    request_data = {
        "prompt_config": "Test prompt",
        "input_schema": {"type": "object", "properties": {"input_key": {"type": "string"}}, "required": ["input_key"]},
        "output_schema": {
            "type": "object",
            "properties": {"output_key": {"type": "string"}},
            "required": ["output_key"],
        },
    }
    response = await client.post("/applications", json=request_data)
    assert response.status_code == 200
    application_id = response.json()["id"]

    # Now, delete the application
    response = await client.delete(f"/applications/{application_id}")
    assert response.status_code == 204

    # Try to get the application logs, should return 404
    response = await client.get(f"/applications/{application_id}/completions/logs")
    assert response.status_code == 404
    assert "Application not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_request_logs(client):
    # First, create an application
    request_data = {
        "prompt_config": "Test prompt",
        "input_schema": {"type": "object", "properties": {"input_key": {"type": "string"}}, "required": ["input_key"]},
        "output_schema": {
            "type": "object",
            "properties": {"output_key": {"type": "string"}},
            "required": ["output_key"],
        },
    }
    response = await client.post("/applications", json=request_data)
    assert response.status_code == 200
    application_id = response.json()["id"]

    # Generate a completion
    inference_request = {"input_data": {"input_key": "test input"}}
    response = await client.post(f"/applications/{application_id}/completions", json=inference_request)
    assert response.status_code == 200

    # Get request logs
    response = await client.get(f"/applications/{application_id}/completions/logs")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) == 1
    log = logs[0]
    assert log["input_data"] == inference_request["input_data"]
    assert log["output_data"] == {"output_key": "mocked_output"}


@pytest.mark.anyio
async def test_get_request_logs_nonexistent_application(client):
    non_existent_application_id = str(uuid.uuid4())
    response = await client.get(f"/applications/{non_existent_application_id}/completions/logs")
    assert response.status_code == 404
    assert "Application not found" in response.json()["detail"]
