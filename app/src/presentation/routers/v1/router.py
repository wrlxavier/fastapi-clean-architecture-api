"""This module defines the version 1 API router."""

from fastapi import APIRouter

from presentation.routers.v1.tasks import router as tasks_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(tasks_router)
