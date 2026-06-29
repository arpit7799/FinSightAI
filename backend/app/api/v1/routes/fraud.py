# app/api/v1/routes/fraud.py
"""
API routes for the Fraud Detection Engine.

Endpoints:
    POST /fraud/{filing_id}/run     - Run fraud detection
    GET  /fraud/{filing_id}         - Get fraud assessment
    GET  /fraud/{filing_id}/beneish - Get Beneish M-Score details
    GET  /fraud/{filing_id}/altman  - Get Altman Z-Score details
    GET  /fraud/flagged/all         - List high-risk fraud filings
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.repositories.fraud_repository import FraudRepository
from app.services.fraud_service import FraudService

router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])


@router.post("/{filing_id}/run")
def run_fraud_detection(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """
    Run fraud detection for a filing.
    Runs Beneish M-Score, Altman Z-Score, and Isolation Forest.
    """
    service = FraudService(db)
    assessment = service.run_fraud_detection(filing_id)

    return {
        "message": "Fraud detection complete",
        "filing_id": filing_id,
        "overall_fraud_score": float(assessment.overall_fraud_score),
        "fraud_risk_class": assessment.fraud_risk_class.value,
        "red_flags_count": len(assessment.red_flags),
    }


@router.get("/{filing_id}")
def get_fraud_assessment(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the complete fraud assessment for a filing."""
    service = FraudService(db)
    assessment = service.get_assessment(filing_id)

    return {
        "filing_id": filing_id,
        "overall_fraud_score": float(assessment.overall_fraud_score) if assessment.overall_fraud_score else None,
        "fraud_risk_class": assessment.fraud_risk_class.value,
        "beneish_score": float(assessment.beneish_score) if assessment.beneish_score else None,
        "beneish_signal": assessment.beneish_signal.value if assessment.beneish_signal else None,
        "altman_score": float(assessment.altman_score) if assessment.altman_score else None,
        "altman_zone": assessment.altman_zone.value if assessment.altman_zone else None,
        "is_anomaly": assessment.is_anomaly,
        "red_flags": assessment.red_flags,
        "narrative": assessment.narrative,
        "created_at": assessment.created_at.isoformat(),
    }


@router.get("/{filing_id}/beneish")
def get_beneish_details(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get detailed Beneish M-Score breakdown.
    Shows all 8 variables with their values and meaning.
    Useful for the fraud dashboard deep-dive view.
    """
    assessment = FraudRepository(db).get_by_filing_id(filing_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="No fraud assessment found. Run /fraud/{filing_id}/run first.")

    return {
        "filing_id": filing_id,
        "m_score": float(assessment.beneish_score) if assessment.beneish_score else None,
        "signal": assessment.beneish_signal.value if assessment.beneish_signal else None,
        "interpretation": "Score > -2.22 indicates likely earnings manipulation",
        "variables": {
            "DSRI": {
                "value": float(assessment.dsri) if assessment.dsri else None,
                "name": "Days Sales Receivable Index",
                "red_flag_threshold": 1.465,
                "description": "Receivables growth vs revenue growth",
            },
            "GMI": {
                "value": float(assessment.gmi) if assessment.gmi else None,
                "name": "Gross Margin Index",
                "red_flag_threshold": 1.193,
                "description": "Gross margin deterioration indicator",
            },
            "AQI": {
                "value": float(assessment.aqi) if assessment.aqi else None,
                "name": "Asset Quality Index",
                "red_flag_threshold": 1.254,
                "description": "Non-current, non-physical asset growth",
            },
            "SGI": {
                "value": float(assessment.sgi) if assessment.sgi else None,
                "name": "Sales Growth Index",
                "red_flag_threshold": 1.607,
                "description": "Revenue growth rate",
            },
            "DEPI": {
                "value": float(assessment.depi) if assessment.depi else None,
                "name": "Depreciation Index",
                "red_flag_threshold": 1.083,
                "description": "Depreciation rate change",
            },
            "SGAI": {
                "value": float(assessment.sgai) if assessment.sgai else None,
                "name": "SGA Expense Index",
                "red_flag_threshold": 1.041,
                "description": "SG&A expense growth vs sales",
            },
            "LVGI": {
                "value": float(assessment.lvgi) if assessment.lvgi else None,
                "name": "Leverage Index",
                "red_flag_threshold": 1.037,
                "description": "Leverage change indicator",
            },
            "TATA": {
                "value": float(assessment.tata) if assessment.tata else None,
                "name": "Total Accruals to Total Assets",
                "red_flag_threshold": 0.031,
                "description": "Earnings quality — accruals vs cash",
            },
        },
    }


@router.get("/{filing_id}/altman")
def get_altman_details(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed Altman Z-Score breakdown."""
    assessment = FraudRepository(db).get_by_filing_id(filing_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="No fraud assessment found.")

    return {
        "filing_id": filing_id,
        "z_score": float(assessment.altman_score) if assessment.altman_score else None,
        "zone": assessment.altman_zone.value if assessment.altman_zone else None,
        "interpretation": {
            "SAFE": "Z > 2.99 — Unlikely to go bankrupt within 2 years",
            "GREY": "1.81 < Z < 2.99 — Uncertain, monitor closely",
            "DISTRESS": "Z < 1.81 — High bankruptcy risk within 2 years",
        }.get(assessment.altman_zone.value if assessment.altman_zone else "", ""),
        "variables": {
            "X1_Working_Capital": float(assessment.altman_x1) if assessment.altman_x1 else None,
            "X2_Retained_Earnings": float(assessment.altman_x2) if assessment.altman_x2 else None,
            "X3_EBIT": float(assessment.altman_x3) if assessment.altman_x3 else None,
            "X4_Equity_Ratio": float(assessment.altman_x4) if assessment.altman_x4 else None,
            "X5_Asset_Turnover": float(assessment.altman_x5) if assessment.altman_x5 else None,
        },
    }


@router.get("/flagged/all")
def get_flagged_filings(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """List all filings with GREY_ZONE or MANIPULATOR fraud signals."""
    assessments = FraudRepository(db).get_high_risk_filings(limit)

    return [
        {
            "filing_id": str(a.filing_id),
            "overall_fraud_score": float(a.overall_fraud_score) if a.overall_fraud_score else None,
            "fraud_risk_class": a.fraud_risk_class.value,
            "beneish_signal": a.beneish_signal.value if a.beneish_signal else None,
            "altman_zone": a.altman_zone.value if a.altman_zone else None,
            "red_flags_count": len(a.red_flags) if a.red_flags else 0,
        }
        for a in assessments
    ]