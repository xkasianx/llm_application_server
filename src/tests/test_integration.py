from uuid import UUID

import pytest
import requests

BASE_URL = "http://localhost:8000"  # The application runs on port 8000 inside Docker Compose


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


def test_create_application(base_url):
    url = f"{base_url}/applications"
    request_data = {
        "prompt_config": "You are a sentiment analysis tool.",
        "input_schema": {
            "type": "object",
            "properties": {"review_text": {"type": "string"}},
            "required": ["review_text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]}},
            "required": ["sentiment"],
        },
    }
    response = requests.post(url, json=request_data)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "id" in data
    assert UUID(data["id"])


def test_generate_response(base_url):
    # Create an application first
    create_app_url = f"{base_url}/applications"
    request_data = {
        "prompt_config": "You are a sentiment analysis tool.",
        "input_schema": {
            "type": "object",
            "properties": {"review_text": {"type": "string"}},
            "required": ["review_text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]}},
            "required": ["sentiment"],
        },
    }
    create_response = requests.post(create_app_url, json=request_data)
    assert create_response.status_code == 200
    app_id = create_response.json()["id"]

    # Now test the completions endpoint
    completions_url = f"{base_url}/applications/{app_id}/completions"
    inference_request = {
        "input_data": {"review_text": "I loved the food at this restaurant! The service was also great."}
    }
    response = requests.post(completions_url, json=inference_request)
    assert response.status_code == 200, response.text
    output_data = response.json()
    assert "sentiment" in output_data
    assert output_data["sentiment"] == "Positive"


def test_get_request_logs(base_url):
    # Create an application first
    create_app_url = f"{base_url}/applications"
    request_data = {
        "prompt_config": "You are a sentiment analysis tool.",
        "input_schema": {
            "type": "object",
            "properties": {"review_text": {"type": "string"}},
            "required": ["review_text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]}},
            "required": ["sentiment"],
        },
    }
    create_response = requests.post(create_app_url, json=request_data)
    assert create_response.status_code == 200
    app_id = create_response.json()["id"]

    # Generate a response to create a log entry
    completions_url = f"{base_url}/applications/{app_id}/completions"
    inference_request = {"input_data": {"review_text": "Great atmosphere and friendly staff."}}
    requests.post(completions_url, json=inference_request)

    # Retrieve logs
    logs_url = f"{base_url}/applications/{app_id}/completions/logs"
    response = requests.get(logs_url)
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    log_entry = logs[0]
    assert "id" in log_entry
    assert "application_id" in log_entry
    assert "input_data" in log_entry
    assert "output_data" in log_entry
    assert "created_at" in log_entry
    assert log_entry["application_id"] == app_id


def test_delete_application(base_url):
    # Create an application first
    create_app_url = f"{base_url}/applications"
    request_data = {
        "prompt_config": "You are a sentiment analysis tool.",
        "input_schema": {
            "type": "object",
            "properties": {"review_text": {"type": "string"}},
            "required": ["review_text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]}},
            "required": ["sentiment"],
        },
    }
    create_response = requests.post(create_app_url, json=request_data)
    assert create_response.status_code == 200
    app_id = create_response.json()["id"]

    # Delete the application
    delete_url = f"{base_url}/applications/{app_id}"
    response = requests.delete(delete_url)
    assert response.status_code == 204

    # Attempt to generate a response with the deleted application
    completions_url = f"{base_url}/applications/{app_id}/completions"
    inference_request = {"input_data": {"review_text": "This should fail."}}
    response = requests.post(completions_url, json=inference_request)
    assert response.status_code == 404
