import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.memory.memory_manager import memory_manager

logger = logging.getLogger("samir.api.conversations")
router = APIRouter(prefix="/conversations", tags=["Conversations Management"])

class ConversationSummary(BaseModel):
    id: str
    title: Optional[str] = "محادثة"
    summary: Optional[str] = ""
    provider_used: Optional[str] = "auto"
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class MessageItem(BaseModel):
    id: int
    sender: str
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    routing_reason: Optional[str] = None
    tool_calls_json: Optional[str] = None
    created_at: Optional[str] = None

@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    device_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """جلب قائمة المحادثات السابقة المعزولة والخاصة بهذا الجهاز أو هذا المستخدم"""
    return await memory_manager.list_conversations(
        limit=limit,
        offset=offset,
        device_id=device_id,
        user_id=user_id,
    )

@router.get("/{conversation_id}/messages", response_model=List[MessageItem])
async def get_conversation_messages(conversation_id: str):
    """جلب تفاصيل ورسائل محادثة معينة"""
    messages = await memory_manager.get_conversation_messages(conversation_id)
    if not messages:
        # Check if conversation exists or just empty
        return []
    return messages

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """حذف محادثة بالكامل وسجل رسائلها"""
    success = await memory_manager.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="فشل في حذف المحادثة")
    return {"status": "success", "message": f"تم حذف المحادثة {conversation_id} بنجاح."}

@router.post("/{conversation_id}/resume")
async def resume_conversation(conversation_id: str):
    """استئناف محادثة قديمة في جلسة العمل النشطة"""
    result = await memory_manager.resume_conversation(conversation_id)
    return result
