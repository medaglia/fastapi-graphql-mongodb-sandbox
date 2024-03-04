import strawberry
from app.routers.gql.jobs import JobResponse, get_jobs
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter

router = APIRouter()


@strawberry.type
class Query:
    get_jobs: JobResponse = strawberry.field(
        description="Get a list of jobs.", resolver=get_jobs
    )


schema = strawberry.Schema(query=Query)
router = GraphQLRouter(schema)
