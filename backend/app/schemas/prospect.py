import uuid
from datetime import datetime
from pydantic import BaseModel


class ProspectRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    full_name: str | None
    email: str | None
    phone: str | None
    website: str | None
    biography: str | None
    followers: int
    following: int
    is_business: bool
    is_verified: bool
    created_at: datetime
