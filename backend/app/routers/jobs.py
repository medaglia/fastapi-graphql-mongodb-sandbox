from typing import Annotated

from app.models.jobs import Job
from app.schemas.jobs import JobBase, JobsResponse, OrganizationsResponse
from beanie.odm.operators.find.evaluation import RegEx
from beanie.odm.operators.find.logical import And, Or
from fastapi import APIRouter, BackgroundTasks, Query

from ..services import usajobs

router = APIRouter()


@router.post("/ingest")
async def ingest(background_tasks: BackgroundTasks):
    """
    Ingest Jobs
    """
    background_tasks.add_task(usajobs.Ingest().ingest_jobs, test_mode=False)
    return {"message": "Ingesting the background"}


@router.get("", response_model=JobsResponse)
async def get_jobs(
    keywords: Annotated[list[str] | None, Query(max_length=50)] = None,
    state: Annotated[str | None, Query(max_length=255)] = None,
    city: Annotated[str | None, Query(max_length=255)] = None,
):
    """Search Jobs"""
    search_criteria_list = []
    if keywords:
        keyword_criteria = Or(
            *[RegEx(Job.title, keyword, options="i") for keyword in keywords]
        )
        search_criteria_list.append(keyword_criteria)

    if state:
        search_criteria_list.append(Job.locations.state == state)

    if city:
        search_criteria_list.append(Job.locations.city == city)

    search_criteria = And(*search_criteria_list) if search_criteria_list else {}

    print("Search Criteria: ", search_criteria)

    total = await Job.find(search_criteria).count()
    newest = (
        await Job.find(search_criteria)
        .sort(-Job.posted_at)
        .limit(1)
        .project(JobBase)
        .to_list()
    )
    oldest = (
        await Job.find(search_criteria)
        .sort(Job.posted_at)
        .limit(1)
        .project(JobBase)
        .to_list()
    )
    return JobsResponse(
        total=total,
        newest=newest[0] if newest else None,
        oldest=oldest[0] if oldest else None,
    )


@router.get("/organizations", response_model=OrganizationsResponse)
async def get_organizations(
    state: Annotated[str | None, Query(max_length=255)] = None,
    city: Annotated[str | None, Query(max_length=255)] = None,
):
    """Get Job Organizations"""
    search_criteria_list = []

    if state:
        search_criteria_list.append(Job.locations.state == state)

    if city:
        search_criteria_list.append(Job.locations.city == city)

    search_criteria = And(*search_criteria_list) if search_criteria_list else {}

    organizations = await Job.distinct(key="organization_name", filter=search_criteria)
    jobs_count = await Job.find(search_criteria).count()

    res = OrganizationsResponse(
        organizations=organizations,
        total_organizations=len(organizations),
        total_jobs=jobs_count,
    )
    print("Res: ", res)
    return res
