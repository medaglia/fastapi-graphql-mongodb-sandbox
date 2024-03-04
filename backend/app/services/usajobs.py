import asyncio
import math
import time
from typing import Optional

import httpx
from app.config.config import settings
from app.models import Job
from app.schemas.services import UsajobsJobResult, UsajobsJobsPage
from beanie import UpdateResponse
from beanie.odm.operators.update.general import Set
from pymongo.results import UpdateResult

# from jobs.models import Job, Location
# from jobs.serializers import LoadJobSerializer, deserialize_city_state

URL = "https://data.usajobs.gov/api/"
MAX_QUERY_LIMIT = 10000
RESULTS_PER_PAGE = 250
MAX_QUERY_LIMIT_MSG = "Max query limit reached. We're likely not getting all jobs"
JOB_CODE_BATCH_SIZE = 5
JOB_PAGE_BATCH_SIZE = 5


# Not available until Python 3.12
def batched(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class IngestJobsException(Exception):
    """A Caption exception occurred"""


class Ingest:
    created_counts = dict(
        jobs=0,
    )

    def get_headers(self):
        return {
            "user-agent": settings.USAJOBS_USER_AGENT,
            "authorization-key": settings.USAJOBS_AUTH_KEY,
        }

    async def ingest_jobs(self, test_mode=False):
        """
        Call USA JOBS API and load jobs into db. If a job already exists in the db, update instead of create.
        """
        print("Ingesting jobs from USA Jobs API")
        start_time = time.time()

        codes = self.get_occupational_codes()

        if test_mode:
            # only ingest the first few codes
            codes[:] = codes[:20]

        async with httpx.AsyncClient() as client:
            for batch in batched(codes, JOB_CODE_BATCH_SIZE):
                print("Running job codes batch:", batch)
                tasks = [
                    self.parameterized_ingest(client, dict(JobCategoryCode=code))
                    for code in batch
                ]
                result_list = await asyncio.gather(*tasks)
                print(f"{sum(result_list)} jobs for codes {batch}")

        elapsed_time = time.time() - start_time
        elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        print(
            f"--------------------------------------------------------------------------------\n"
            f"Finished ingesting jobs\n"
            f"Created {self.created_counts['jobs']} jobs\n"
            f"Elapsed time: {elapsed_time_str}\n"
            f"--------------------------------------------------------------------------------"
        )

    async def parameterized_ingest(
        self,
        client: httpx.AsyncClient,
        query_params: Optional[dict[str, str]],
    ) -> int:
        """Ingest jobs from the USA Jobs API with the given query parameters.

        First requests jobs from the USA Jobs API, handling paginated responses if necessary. Then loads each job into the database.
        """

        print("Ingesting jobs with params:", query_params)
        params = dict(Page=1, ResultsPerPage=RESULTS_PER_PAGE)
        params.update(query_params)

        page = await self.get_page(client, params=params)
        results = page.results

        if page.count_all > RESULTS_PER_PAGE:
            # Get the rest of the pages
            more_pages = list(
                range(2, math.ceil(page.count_all / RESULTS_PER_PAGE) + 1)
            )
            results += await self.get_pages(client, more_pages, params=params)

        for job in results:
            await self.load_job(job)

        return len(results)

    async def get_pages(
        self,
        client: httpx.AsyncClient,
        pages: list[int],
        params: Optional[dict[str, str]],
    ) -> list[UsajobsJobResult]:
        """Get batched pages of jobs from the USA Jobs API."""
        page_results = []
        jobs = []

        for batch in batched(pages, JOB_PAGE_BATCH_SIZE):
            tasks = []
            for page in batch:
                tasks.append(self.get_page(client, dict(params, Page=page)))
            page_results += await asyncio.gather(*tasks)

        for p in page_results:
            jobs += p.results

        return jobs

    async def get_page(
        self, client: httpx.AsyncClient, params: Optional[dict[str, str]]
    ) -> UsajobsJobsPage:
        """Get a single page of jobs from the USA Jobs API. Return the total results and the results."""

        url = f"{URL}/search"
        print("Getting page with params:", params)
        r = await client.get(url, headers=self.get_headers(), params=params)

        if r.status_code != httpx.codes.OK:
            raise IngestJobsException(f"Bad response from external api: {url}")

        page = UsajobsJobsPage.model_validate(r.json())

        if page.count_all >= MAX_QUERY_LIMIT:
            print("Max query limit reached. We're likely not getting all jobs", params)
            raise IngestJobsException(MAX_QUERY_LIMIT_MSG)

        return page

    async def load_job(self, result: UsajobsJobResult):
        """Load a single job into the database."""

        # Create the job
        try:
            resp = await Job.find_one({"external_id": result.external_id}).upsert(
                Set(result.dict()),
                on_insert=result,
                response_type=UpdateResponse.UPDATE_RESULT,
            )

            # Insert response: id=ObjectId('65c93ef4a93fbe10f495b3b6') revision_id=None title='INTERDISCIPLINARY COMMUNITY PLANNER/BIOLOGIST/ENVIRONMENTAL ENGINEER/PHYSICAL SCIENTIST' external_id='768104100' posted_at=datetime.datetime(2024, 1, 3, 13, 36, 30, 203000) organization_name='Naval Facilities Engineering Systems Command' locations=[UsajobsJobLocation(city='Honolulu', state='Hawaii'), UsajobsJobLocation(city='Pearl Harbor', state='Hawaii')]
            # Update response: UpdateResult({'n': 1, 'nModified': 1, 'ok': 1.0, 'updatedExisting': True}, acknowledged=True)

            if isinstance(resp, UpdateResult):
                print("Updated job:", resp)
            else:
                self.created_counts["jobs"] += 1
                print("Created job:", resp.external_id)

        except Exception as e:
            print(f"Error loading job: {result.external_id}", e)

    def get_occupational_codes(self):
        """Get all Occupational codes from the USA Jobs API."""

        url = f"{URL}/codelist/occupationalseries"
        r = httpx.get(url, headers=self.get_headers())

        if r.status_code != httpx.codes.OK:
            raise IngestJobsException(f"Bad response from external api: {url}")

        return [value["Code"] for value in r.json()["CodeList"][0]["ValidValue"]]
