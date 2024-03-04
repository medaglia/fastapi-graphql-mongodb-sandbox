from datetime import datetime
from typing import Annotated

from app.models.jobs import Job, Location
from pydantic import AfterValidator, AliasPath, BaseModel, Field


def deserialize_city(location: str) -> str:
    """Deserialize a location string into city."""
    city_state = location.lower().split(", ")
    return ", ".join(city_state[0:-1])


def deserialize_state(location: str) -> str:
    """Deserialize a location string into state."""
    city_state = location.lower().split(", ")
    return city_state[-1]


City = Annotated[str, AfterValidator(deserialize_city)]
State = Annotated[str, AfterValidator(deserialize_state)]


class UsajobsJobLocation(Location):
    """
    Location of a job ingested from UsaJobs
    """

    city: City = Field(validation_alias=AliasPath("CityName"))
    state: State = Field(validation_alias=AliasPath("CityName"))
    label: str = Field(validation_alias=AliasPath("CityName"))


class UsajobsJobResult(Job):
    """
    Job result ingested from UsaJobs
    """

    external_id: str = Field(validation_alias=AliasPath("MatchedObjectId"))
    title: str = Field(
        max_length=255,
        validation_alias=AliasPath("MatchedObjectDescriptor", "PositionTitle"),
    )
    posted_at: datetime = Field(
        validation_alias=AliasPath("MatchedObjectDescriptor", "PublicationStartDate")
    )
    organization_name: str = Field(
        max_length=255,
        validation_alias=AliasPath("MatchedObjectDescriptor", "OrganizationName"),
    )
    locations: list[UsajobsJobLocation] = Field(
        validation_alias=AliasPath("MatchedObjectDescriptor", "PositionLocation")
    )


class UsajobsJobsPage(BaseModel):
    results: list[UsajobsJobResult] = Field(
        validation_alias=AliasPath("SearchResult", "SearchResultItems")
    )
    Language: str = Field(validation_alias=AliasPath("LanguageCode"))
    count_all: int = Field(
        validation_alias=AliasPath("SearchResult", "SearchResultCountAll")
    )
