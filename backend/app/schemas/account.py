import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    username: str = Field(max_length=150)
    session_json: str  # JSON string from instagrapi -- NO password
    # Required (audit C1): a proxy-less account shares the deployment host's
    # IP with every other proxy-less account, which reads to Instagram as
    # one IP running multiple sessions.
    proxy_url: str = Field(max_length=500)
    # Optional instagrapi locale (e.g. "pt_BR") matching the proxy's country
    # -- geo-matches the device to its egress IP (audit AUDIT-2.md M5).
    locale: str | None = Field(default=None, max_length=10)


class AccountRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    proxy_url: str
    locale: str | None
    status: str
    requests_today: int
    last_used_at: datetime | None
    cooldown_until: datetime | None
    created_at: datetime
    # NOTE: session_json intentionally excluded -- never returned via API
