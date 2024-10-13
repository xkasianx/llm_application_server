import json
import uuid

from fastapi import Depends
from jsonschema import Draft7Validator, ValidationError, validate
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from src.config import settings
from src.database import models
from src.database.session import get_db_session
from src.exceptions import (
    ApplicationNotFoundException,
    InputValidationException,
    LLMCallException,
    OutputValidationException,
    SchemaValidationException,
)

openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
)


class ApplicationService:
    def __init__(self, db_session: AsyncSession):
        self._session = db_session

    async def create_application(
        self,
        prompt_config: str,
        input_schema: dict,
        output_schema: dict,
    ) -> models.Application:
        try:
            Draft7Validator.check_schema(input_schema)
            Draft7Validator.check_schema(output_schema)
        except Exception as e:
            raise SchemaValidationException(f"Schema validation error: {str(e)}")

        application = models.Application(
            prompt_config=prompt_config, input_schema=input_schema, output_schema=output_schema
        )
        self._session.add(application)
        await self._session.commit()
        await self._session.refresh(application)
        return application

    async def get_application(self, application_id: uuid.UUID) -> models.Application:
        application = await self._session.get(models.Application, application_id)
        if not application:
            raise ApplicationNotFoundException("Application not found")
        return application

    async def delete_application(self, application_id: uuid.UUID) -> None:
        application = await self.get_application(application_id)

        await self._session.delete(application)
        return

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    async def _call_llm(self, prompt_config: str, input_data: dict, output_schema: dict) -> dict:
        chat_completion = await openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_config},
                {"role": "user", "content": json.dumps(input_data)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response_schema",
                    "schema": {**output_schema, "additionalProperties": False},
                    "strict": True,
                },
            },
            model=settings.OPENAI_MODEL,
        )
        return chat_completion

    async def generate_completion(
        self,
        application_id: uuid.UUID,
        input_data: dict,
    ) -> dict:
        application = await self.get_application(application_id)

        try:
            validate(instance=input_data, schema=application.input_schema)
        except ValidationError as e:
            raise InputValidationException(f"Input validation failed: {str(e)}")

        try:
            chat_completion = await self._call_llm(
                prompt_config=application.prompt_config, input_data=input_data, output_schema=application.output_schema
            )
        except Exception as e:
            raise LLMCallException(f"LLM call failed: {str(e)}")

        try:
            output_data = json.loads(chat_completion.choices[0].message.content)
            validate(instance=output_data, schema=application.output_schema)
        except ValidationError as e:
            raise OutputValidationException(f"Output validation failed: {str(e)}")

        completion_log = models.CompletionLog(
            application_id=application_id, input_data=input_data, output_data=output_data
        )
        self._session.add(completion_log)
        return output_data

    async def get_request_logs(
        self, application_id: uuid.UUID, page: int, size: int
    ) -> tuple[list[models.CompletionLog], int]:
        await self.get_application(application_id)

        offset = (page - 1) * size

        logs_query = (
            select(models.CompletionLog)
            .where(models.CompletionLog.application_id == application_id)
            .order_by(models.CompletionLog.created_at.desc())
            .limit(size)
            .offset(offset)
        )
        logs_result = await self._session.execute(logs_query)
        paginated_logs = logs_result.scalars().all()

        count_query = (
            select(func.count())
            .select_from(models.CompletionLog)
            .where(models.CompletionLog.application_id == application_id)
        )
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        return paginated_logs, total


async def get_application_service(
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationService:
    return ApplicationService(session)
