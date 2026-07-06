from fastapi import APIRouter

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats")
def dashboard_stats():
    return {
        "companies": 0,
        "reports": 0,
        "analyses": 0,
        "generated_reports": 0
    }