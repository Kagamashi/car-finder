import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationLogRead(BaseModel):
    id: uuid.UUID
    filter_id: uuid.UUID
    listing_id: uuid.UUID
    sent_at: datetime
    status: str
    error_msg: str | None

    model_config = {"from_attributes": True}
