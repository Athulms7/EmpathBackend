from sqlalchemy import String, ForeignKey, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base
import uuid

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), unique=True
    )

    data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict
    )

    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    case_summary: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    conversation = relationship("Conversation", back_populates="incident")
