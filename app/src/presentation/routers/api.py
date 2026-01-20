"""This module defines the main API router that includes versioned routers."""

from fastapi import APIRouter

from presentation.routers.health import router as health_router
from presentation.routers.v1 import v1_router

api_router = APIRouter()
api_router.include_router(v1_router)
api_router.include_router(health_router)
