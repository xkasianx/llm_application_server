import json
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture(scope="module", autouse=True)
def mock_call_llm():
    with patch("src.service.ApplicationService._call_llm", new_callable=AsyncMock) as mock_method:
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
    # Create an application
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
    response_data = response.json()
    assert "output_data" in response_data
    assert response_data["output_data"] == {"output_key": "mocked_output"}


@pytest.mark.anyio
async def test_generate_completion_invalid_input(client):
    # Create an application
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

    # Generate a completion with invalid input
    inference_request = {"input_data": {"input_key": 123}}  # Invalid type, should be string
    response = await client.post(f"/applications/{application_id}/completions", json=inference_request)
    assert response.status_code == 400
    assert "Input validation failed" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_application(client):
    # Create an application
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

    # Delete the application
    response = await client.delete(f"/applications/{application_id}")
    assert response.status_code == 204

    # Try to get the application logs, should return 404
    response = await client.get(f"/applications/{application_id}/completions/logs")
    assert response.status_code == 404
    assert "Application not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_request_logs_paginated(client):
    # Create an application
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
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    application_id = response.json()["id"]

    # Generate multiple completions to test pagination
    num_completions = 25
    for _ in range(num_completions):
        inference_request = {"input_data": {"input_key": "test input"}}
        response = await client.post(f"/applications/{application_id}/completions", json=inference_request)
        assert response.status_code == 200, f"Unexpected status code during completion creation: {response.status_code}"

    # Define pagination parameters
    page = 2
    size = 10

    # Get request logs with pagination
    response = await client.get(f"/applications/{application_id}/completions/logs", params={"page": page, "size": size})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

    logs_response = response.json()

    # Validate response structure
    assert isinstance(logs_response, dict), "Response is not a dictionary"
    assert "total" in logs_response, "Missing 'total' in response"
    assert "page" in logs_response, "Missing 'page' in response"
    assert "size" in logs_response, "Missing 'size' in response"
    assert "total_pages" in logs_response, "Missing 'total_pages' in response"
    assert "items" in logs_response, "Missing 'items' in response"

    # Validate pagination metadata
    assert logs_response["total"] == num_completions, f"Expected total {num_completions}, got {logs_response['total']}"
    assert logs_response["page"] == page, f"Expected page {page}, got {logs_response['page']}"
    assert logs_response["size"] == size, f"Expected size {size}, got {logs_response['size']}"
    expected_total_pages = (num_completions + size - 1) // size  # Ceiling division
    assert (
        logs_response["total_pages"] == expected_total_pages
    ), f"Expected total_pages {expected_total_pages}, got {logs_response['total_pages']}"

    # Validate items
    items = logs_response["items"]
    assert isinstance(items, list), "'items' is not a list"
    expected_items = size if page < expected_total_pages else num_completions - size * (expected_total_pages - 1)
    assert len(items) == expected_items, f"Expected {expected_items} items on page {page}, got {len(items)}"

    for log in items:
        assert "input_data" in log, "Missing 'input_data' in log"
        assert "output_data" in log, "Missing 'output_data' in log"
        assert log["input_data"] == {"input_key": "test input"}, "Incorrect 'input_data' in log"
        assert log["output_data"] == {"output_key": "mocked_output"}, "Incorrect 'output_data' in log"


@pytest.mark.anyio
async def test_get_request_logs_nonexistent_application_paginated(client):
    # Generate a random UUID for a non-existent application
    non_existent_application_id = str(uuid.uuid4())

    # Attempt to get request logs with default pagination parameters
    response = await client.get(f"/applications/{non_existent_application_id}/completions/logs")
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"

    error_response = response.json()
    assert "detail" in error_response, "Missing 'detail' in error response"
    assert "Application not found" in error_response["detail"], f"Unexpected error detail: {error_response['detail']}"
