from datetime import datetime
from typing import Optional

from app.models import Job
from pydantic import BaseModel


class JobLocation(BaseModel):
    city: str
    state: str


class JobBase(BaseModel):
    title: str
    posted_at: datetime
    locations: list[JobLocation]


class JobsResponse(BaseModel):
    total: int
    newest: Optional[JobBase]
    oldest: Optional[JobBase]


class OrganizationsResponse(BaseModel):
    organizations: list[str]
    total_organizations: int
    total_jobs: int
