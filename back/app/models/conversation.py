from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base
import uuid

# class Conversation(Base):
#     __tablename__ = "conversations"

#     id: Mapped[str] = mapped_column(
#         String, primary_key=True, default=lambda: str(uuid.uuid4())
#     )
#     user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
#     title: Mapped[str] = mapped_column(String)
#     created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

#     user = relationship("User", back_populates="conversations")
#     messages = relationship("Message", back_populates="conversation", cascade="all,delete")

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all,delete"
    )

   
    incident = relationship(
        "Incident",
        back_populates="conversation",
        uselist=False,
        cascade="all,delete"
    )