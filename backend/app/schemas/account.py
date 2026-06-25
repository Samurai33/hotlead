import uuid
from datetime import datetime

from pydantic import BaseModel


class AccountCreate(BaseModel):
    username:     str
    session_json: str        # JSON string from instagrapi -- NO password
    proxy_url:    str | None = None


class AccountRead(BaseModel):
    model_config = {"from_attributes": True}

    id:             uuid.UUID
    username:       str
    proxy_url:      str | None
    status:         str
    requests_today: int
    last_used_at:   datetime | None
    cooldown_until: datetime | None
    created_at:     datetime
    # NOTE: session_json intentionally excluded -- never returned via API
