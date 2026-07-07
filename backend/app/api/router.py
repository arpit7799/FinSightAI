from fastapi import APIRouter

from app.api.company import router as company_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.report import router as report_router
from app.api.ocr import router as ocr_router
from app.api.nlp import router as nlp_router
from app.api.financial_data import router as financial_data_router
from app.api.financial_ratio import router as financial_ratio_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(company_router)
api_router.include_router(report_router)
api_router.include_router(ocr_router)
api_router.include_router(nlp_router)
api_router.include_router(financial_data_router)
api_router.include_router(financial_ratio_router)