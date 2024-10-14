from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel


class ApplicationCreateRequest(BaseModel):
    prompt_config: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class ApplicationCreateResponse(BaseModel):
    id: UUID

    class Config:
        from_attributes = True


class ApplicationInferenceRequest(BaseModel):
    input_data: Dict[str, Any]


class ApplicationInferenceResponse(BaseModel):
    output_data: Dict[str, Any]


class CompletionLog(BaseModel):
    id: UUID
    application_id: UUID
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedCompletionLogResponse(BaseModel):
    total: int
    page: int
    size: int
    total_pages: int
    items: list[CompletionLog]
