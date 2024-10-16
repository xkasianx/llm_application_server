import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import src.schemas as schemas
from src.database.session import get_db_session
from src.exceptions import (
    ApplicationNotFoundException,
    InputValidationException,
    OutputValidationException,
    SchemaValidationException,
)
from src.service import ApplicationService, get_application_service

app = FastAPI(title="LLM Application Server")


@app.get("/health")
async def health(session: AsyncSession = Depends(get_db_session)):
    try:
        await session.execute(select(1))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}


@app.post("/applications")
async def create_application(
    request: schemas.ApplicationCreateRequest,
    application_service: ApplicationService = Depends(get_application_service),
) -> schemas.ApplicationCreateResponse:
    try:
        application = await application_service.create_application(
            prompt_config=request.prompt_config, input_schema=request.input_schema, output_schema=request.output_schema
        )
    except SchemaValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return schemas.ApplicationCreateResponse.model_validate(application)


@app.delete("/applications/{application_id}", status_code=204)
async def delete_application(
    application_id: uuid.UUID, application_service: ApplicationService = Depends(get_application_service)
):
    try:
        await application_service.delete_application(application_id)
    except ApplicationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return


@app.post("/applications/{application_id}/completions")
async def generate_response(
    application_id: uuid.UUID,
    request: schemas.ApplicationInferenceRequest,
    application_service: ApplicationService = Depends(get_application_service),
) -> schemas.ApplicationInferenceResponse:
    try:
        output_data = await application_service.generate_completion(
            input_data=request.input_data, application_id=application_id
        )
    except ApplicationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InputValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OutputValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return schemas.ApplicationInferenceResponse(output_data=output_data)


@app.get("/applications/{application_id}/completions/logs")
async def get_request_logs(
    application_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    size: int = Query(10, ge=1, description="Number of items per page"),
    application_service: ApplicationService = Depends(get_application_service),
) -> schemas.PaginatedCompletionLogResponse:
    try:
        paginated_logs, total = await application_service.get_request_logs(application_id, page, size)
    except ApplicationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    total_pages = (total + size - 1) // size

    return schemas.PaginatedCompletionLogResponse(
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
        items=[schemas.CompletionLog.model_validate(log) for log in paginated_logs],
    )
