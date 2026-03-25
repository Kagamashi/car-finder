import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.notification import NotificationLogRead
from app.services import notification_service

router = APIRouter()

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[NotificationLogRead])
async def list_notifications(
    db: DB,
    filter_id: uuid.UUID | None = Query(None),
    listing_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await notification_service.get_notification_log(
        db,
        filter_id=filter_id,
        listing_id=listing_id,
        limit=limit,
        offset=offset,
    )
