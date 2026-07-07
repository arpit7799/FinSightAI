from fastapi import APIRouter

from app.api.company import router as company_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(company_router)