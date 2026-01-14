from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from datetime import datetime

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/profile")
def profile(user=Depends(get_current_user)):
    return user

@router.delete("/delete")
def delete_account(user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"success": True}

@router.get("/export")
def export_data(user=Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = db.query(Conversation).filter_by(user_id=user.id).all()
    messages = db.query(Message).join(Conversation).filter(Conversation.user_id == user.id).all()
    return {
        "conversations": conversations,
        "messages": messages,
        "exportedAt": datetime.utcnow()
    }
