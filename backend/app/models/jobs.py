from datetime import datetime
from typing import Annotated

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel


class Location(BaseModel):
    city: str
    state: str
    label: str


class Job(Document):

    class Settings:
        indexes = [
            [
                ("locations.state", pymongo.ASCENDING),
                ("locations.city", pymongo.ASCENDING),
            ],
        ]

    title: Annotated[str, Indexed(index_type=pymongo.TEXT)]
    external_id: Annotated[str, Indexed(unique=True)]
    posted_at: datetime
    organization_name: str
    locations: list[Location]
