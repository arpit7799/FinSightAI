from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.ml.risk import router as risk_router
from app.api.ml.fraud import router as fraud_router
from app.api.ml.forecast import router as forecast_router
from app.api.analysis import router as analysis_router
from app.api.stock_data import router as stock_data_router

from app.api.router import api_router
from app.config import settings
from app.core.logging import logger

import app.models
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FinSight AI Backend")
    yield
    logger.info("Stopping FinSight AI Backend")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

app.include_router(api_router)
app.include_router(risk_router)
app.include_router(fraud_router)
app.include_router(forecast_router)
app.include_router(analysis_router)
app.include_router(stock_data_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to FinSight AI",
        "version": settings.APP_VERSION,
    }