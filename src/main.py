import json
import uuid
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from jsonschema import Draft7Validator, ValidationError, validate
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models
from config import settings
from database import models as db_models
from database.session import get_db_session

app = FastAPI(title="LLM Application Server")

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_db_session)):
    try:
        await session.execute(select(1))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}


@app.post("/applications")
async def create_application(
    request: models.ApplicationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> models.ApplicationCreateResponse:
    try:
        Draft7Validator.check_schema(request.input_schema)
        Draft7Validator.check_schema(request.output_schema)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Schema validation error: {str(e)}")

    application = db_models.Application(**request.dict())
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return models.ApplicationCreateResponse.from_orm(application)


@app.delete("/applications/{application_id}")
async def delete_application(application_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    application = await session.get(db_models.Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    await session.delete(application)
    await session.commit()
    return


@app.post("/applications/{application_id}/completions")
async def generate_response(
    application_id: uuid.UUID,
    request: models.ApplicationInferenceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> models.ApplicationInferenceResponse:
    application = await session.get(db_models.Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        validate(instance=request.input_data, schema=application.input_schema)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Input validation error: {str(e)}")

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": application.prompt_config},
                {"role": "user", "content": json.dumps(request.input_data)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response_schema",
                    "schema": {**application.output_schema, "additionalProperties": False},
                    "strict": True,
                },
            },
            model=settings.OPENAI_MODEL,
        )
        output_data = json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

    try:
        validate(instance=output_data, schema=application.output_schema)
    except ValidationError as e:
        raise HTTPException(status_code=500, detail=f"LLM output validation failed: {str(e)}")

    completion_log = db_models.CompletionLog(
        application_id=application_id, input_data=request.input_data, output_data=output_data
    )
    session.add(completion_log)
    await session.commit()

    return models.ApplicationInferenceResponse(output_data=output_data)


@app.get("/applications/{application_id}/completions/logs")
async def get_request_logs(
    application_id: str, session: AsyncSession = Depends(get_db_session)
) -> List[models.CompletionLogResponse]:  # TODO: maybe add pagination
    logs = await session.scalars(
        select(db_models.CompletionLog)
        .filter_by(application_id=application_id)
        .order_by(db_models.CompletionLog.created_at.desc())
    )

    return [models.CompletionLogResponse.from_orm(log) for log in logs]
