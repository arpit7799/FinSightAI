# app/main.py

from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.analysis import router as analysis_router
from app.api.v1.routes.rag import router as rag_router
from app.api.v1.routes.risk import router as risk_router
from app.api.v1.routes.fraud import router as fraud_router           # NEW
from app.core.exceptions import (
    FilingNotFound,
    ProcessingError,
    UnauthorizedAccess,
    UserAlreadyExists,
)
from app.core.logging import configure_logging

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", service="FinSight AI")
    yield
    logger.info("application_shutdown", service="FinSight AI")


app = FastAPI(
    title="FinSight AI",
    version="1.0.0",
    description="AI-powered Financial Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = round(time.time() - start_time, 4)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency=process_time,
        user_id=getattr(request.state, "user_id", None),
    )
    return response


@app.exception_handler(FilingNotFound)
async def filing_not_found_handler(request: Request, exc: FilingNotFound):
    return JSONResponse(status_code=404, content={"error": exc.detail})

@app.exception_handler(UnauthorizedAccess)
async def unauthorized_handler(request: Request, exc: UnauthorizedAccess):
    return JSONResponse(status_code=403, content={"error": exc.detail})

@app.exception_handler(ProcessingError)
async def processing_handler(request: Request, exc: ProcessingError):
    return JSONResponse(status_code=500, content={"error": exc.detail})

@app.exception_handler(UserAlreadyExists)
async def user_exists_handler(request: Request, exc: UserAlreadyExists):
    return JSONResponse(status_code=400, content={"error": exc.detail})


app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(fraud_router, prefix="/api/v1")                   # NEW


@app.get("/")
def root():
    return {"message": "FinSight AI API Running"}

@app.get("/health")
def health():
    return {"status": "healthy"}