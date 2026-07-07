from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.company import Company
from app.models.report import Report
from app.models.nlp_analysis import NLPAnalysis

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    companies = db.query(func.count(Company.id)).scalar() or 0
    reports = db.query(func.count(Report.id)).scalar() or 0
    analyses = db.query(func.count(NLPAnalysis.id)).scalar() or 0
    
    return {
        "companies": companies,
        "reports": reports,
        "analyses": analyses,
        "generated_reports": reports
    }