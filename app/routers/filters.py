import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.filter import FilterCreate, FilterRead, FilterUpdate
from app.services import filter_service

router = APIRouter()

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_user_or_404(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post(
    "/users/{user_id}/filters",
    response_model=FilterRead,
    status_code=status.HTTP_201_CREATED,
    tags=["filters"],
)
async def create_filter(user_id: uuid.UUID, body: FilterCreate, db: DB):
    await _get_user_or_404(user_id, db)
    f = await filter_service.create_filter(db, user_id, body)
    return f


@router.get("/users/{user_id}/filters", response_model=list[FilterRead], tags=["filters"])
async def list_filters(user_id: uuid.UUID, db: DB):
    await _get_user_or_404(user_id, db)
    return await filter_service.get_filters_for_user(db, user_id)


@router.put("/users/{user_id}/filters/{filter_id}", response_model=FilterRead, tags=["filters"])
async def update_filter(user_id: uuid.UUID, filter_id: uuid.UUID, body: FilterUpdate, db: DB):
    await _get_user_or_404(user_id, db)
    f = await filter_service.get_filter(db, filter_id)
    if f is None or f.user_id != user_id:
        raise HTTPException(status_code=404, detail="Filter not found")
    return await filter_service.update_filter(db, f, body)


@router.delete(
    "/users/{user_id}/filters/{filter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["filters"],
)
async def delete_filter(user_id: uuid.UUID, filter_id: uuid.UUID, db: DB):
    await _get_user_or_404(user_id, db)
    f = await filter_service.get_filter(db, filter_id)
    if f is None or f.user_id != user_id:
        raise HTTPException(status_code=404, detail="Filter not found")
    await filter_service.delete_filter(db, f)
