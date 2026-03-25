from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

# Convenience type alias for injecting a DB session into route handlers
DBSession = Annotated[AsyncSession, Depends(get_db)]
