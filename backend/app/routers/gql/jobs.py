import datetime
from typing import Any, Optional

import strawberry
from app.models.jobs import Job
from app.routers.pagination import CursorPagination, PageMeta, PaginatedResult
from beanie.odm.operators.find.evaluation import RegEx
from beanie.odm.operators.find.logical import And, Or


@strawberry.type
class Location:
    city: str
    state: str


@strawberry.type
class JobResult(PaginatedResult):
    title: str
    external_id: str
    posted_at: datetime.datetime
    organization_name: str
    locations: list[Location]


@strawberry.type
class JobResponse:
    page_meta: PageMeta = strawberry.field(description="Metadata to aid in pagination.")
    jobs: list[JobResult] = strawberry.field(description="The list of jobs.")


async def get_jobs(
    self,
    keywords: Optional[list[str]] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    limit: Optional[int] = 4,
    cursor: Optional[str] = None,
) -> JobResponse:

    search_criteria_list: list[Any] = []

    if keywords:
        keyword_criteria = Or(
            *[RegEx(Job.title, keyword, options="i") for keyword in keywords]
        )
        search_criteria_list.append(keyword_criteria)

    if state:
        search_criteria_list.append(Job.locations.state == state.lower())

    if city:
        search_criteria_list.append(Job.locations.city == city.lower())

    search_criteria = And(*search_criteria_list) if search_criteria_list else {}

    pagination = CursorPagination(limit=limit, cursor=cursor)
    await pagination.paginate(Job.find(search_criteria), Job.external_id)

    return JobResponse(
        jobs=pagination.results,
        page_meta=PageMeta(next_cursor=pagination.next_cursor),
    )
