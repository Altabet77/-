import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.core.activity_log import activity_logger

logger = logging.getLogger("samir.api.logs")
router = APIRouter(prefix="/logs", tags=["Activity Logs"])


@router.get("/")
async def get_activity_logs(limit: int = Query(50, ge=1, le=200)):
    """جلب سجل العمليات الأخيرة"""
    try:
        logs = await activity_logger.get_recent_logs(limit=limit)
        return {
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/")
async def clear_activity_logs():
    """حذف جميع سجلات العمليات"""
    try:
        deleted_count = await activity_logger.clear_logs()
        return {
            "deleted": True,
            "count": deleted_count,
            "message": f"تم حذف {deleted_count} سجل."
        }
    except Exception as e:
        logger.error(f"Error clearing logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
