import uuid
from datetime import datetime
from typing import List

from sqlalchemy import JSON, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

Base = declarative_base()


class Application(Base):

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    prompt_config: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    completion_logs: Mapped[List["CompletionLog"]] = relationship(
        back_populates="application",
    )


class CompletionLog(Base):

    __tablename__ = "completion_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{Application.__tablename__}.id"),
        nullable=False,
        index=True,
    )
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    application: Mapped["Application"] = relationship(back_populates="completion_logs")
