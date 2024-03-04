from fastapi import APIRouter

from . import graphql, jobs, login, users

api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(graphql.router, prefix="/graphql", tags=["graphql"])


@api_router.get("/")
async def root():
    return {"message": "Backend API for FARM-docker operational !"}
