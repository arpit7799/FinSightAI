# app/api/v1/routes/risk.py
"""
API routes for the Risk Prediction Engine.

Endpoints:
    POST /risk/{filing_id}/run     - Run risk prediction
    GET  /risk/{filing_id}         - Get risk prediction result
    GET  /risk/{filing_id}/shap    - Get SHAP explanation data
    GET  /risk/high-risk           - List highest risk filings
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.services.risk_service import RiskService
from app.repositories.risk_repository import RiskRepository

router = APIRouter(prefix="/risk", tags=["Risk Prediction"])


@router.post("/{filing_id}/run")
def run_risk_prediction(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """
    Run the ML risk prediction for a filing.
    Requires financial analysis to be complete first.
    """
    service = RiskService(db)
    prediction = service.run_risk_prediction(filing_id)

    return {
        "message": "Risk prediction complete",
        "filing_id": filing_id,
        "risk_score": float(prediction.risk_score),
        "risk_class": prediction.risk_class.value,
    }


@router.get("/{filing_id}")
def get_risk_prediction(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get the full risk prediction result for a filing.
    Includes score, class, top factors, and AI narrative.
    """
    service = RiskService(db)
    prediction = service.get_prediction(filing_id)

    return {
        "filing_id": filing_id,
        "risk_score": float(prediction.risk_score),
        "risk_class": prediction.risk_class.value,
        "xgb_score": float(prediction.xgb_score) if prediction.xgb_score else None,
        "lgbm_score": float(prediction.lgbm_score) if prediction.lgbm_score else None,
        "top_factors": prediction.top_factors,
        "narrative": prediction.narrative,
        "model_version": prediction.model_version,
        "created_at": prediction.created_at.isoformat(),
    }


@router.get("/{filing_id}/shap")
def get_shap_explanation(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get SHAP values for the risk prediction.
    Used by the frontend to render the SHAP waterfall chart.
    """
    prediction = RiskRepository(db).get_by_filing_id(filing_id)

    if not prediction:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail="No risk prediction found. Run /risk/{filing_id}/run first."
        )

    return {
        "filing_id": filing_id,
        "shap_values": prediction.shap_values,
        "base_value": float(prediction.shap_base_value) if prediction.shap_base_value else None,
        "feature_vector": prediction.feature_vector,
        "top_factors": prediction.top_factors,
        # Chart-ready format for Recharts on the frontend
        "chart_data": [
            {
                "feature": factor["factor"],
                "impact": factor["impact"],
                "direction": factor["direction"],
                "value": factor["feature_value"],
            }
            for factor in (prediction.top_factors or [])
        ],
    }


@router.get("/high-risk/all")
def get_high_risk_filings(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """Get the highest risk filings across all companies."""
    predictions = RiskRepository(db).get_high_risk_filings(limit)

    return [
        {
            "filing_id": str(p.filing_id),
            "risk_score": float(p.risk_score),
            "risk_class": p.risk_class.value,
            "top_factors": p.top_factors[:2] if p.top_factors else [],
        }
        for p in predictions
    ]