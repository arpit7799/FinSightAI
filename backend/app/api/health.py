from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
def health():
    return {
        "status": "healthy",
        "message": "FinSight AI Backend Running"
    }