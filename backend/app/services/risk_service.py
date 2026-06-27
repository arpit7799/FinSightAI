# app/services/risk_service.py
"""
Orchestrates the full risk prediction pipeline.

Steps:
1. Load ratios from Phase 5
2. Build feature vector
3. Run XGBoost + LightGBM scorer
4. Generate SHAP explanation
5. Generate Llama 3 narrative
6. Save to DB
"""

import pickle
import os
import structlog
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.domain.models.risk_prediction import RiskPrediction
from app.domain.models.enums import RiskClass
from app.engines.risk.feature_engineer import build_feature_vector, features_to_list
from app.engines.risk.risk_scorer import RiskScorer
from app.engines.risk.shap_explainer import SHAPExplainer
from app.engines.risk.risk_narrative import generate_risk_narrative
from app.repositories.filing_repository import FilingRepository
from app.repositories.ratio_repository import RatioRepository
from app.repositories.statement_repository import StatementRepository
from app.repositories.risk_repository import RiskRepository

logger = structlog.get_logger()

MODELS_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../../ml/models"
)

MODEL_VERSION = "v1.0"


class RiskService:

    def __init__(self, db: Session):
        self.db = db
        self.filing_repo = FilingRepository(db)
        self.ratio_repo = RatioRepository(db)
        self.statement_repo = StatementRepository(db)
        self.risk_repo = RiskRepository(db)

    def run_risk_prediction(self, filing_id: str) -> RiskPrediction:
        """
        Run the full risk prediction pipeline for a filing.
        Returns the saved RiskPrediction record.
        """
        # ── Check filing exists ───────────────────────────────────────────
        filing = self.filing_repo.get_by_id(filing_id)
        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")

        # ── Load ratios from Phase 5 ──────────────────────────────────────
        ratios = self.ratio_repo.get_by_filing_id(filing_id)
        if not ratios:
            raise HTTPException(
                status_code=422,
                detail="No ratios found. Run financial analysis first (/api/v1/analysis/{filing_id}/run)",
            )

        # ── Load normalized financial data ────────────────────────────────
        normalized_data = self.statement_repo.get_normalized_data(filing_id)

        logger.info("risk_prediction_started", filing_id=filing_id)

        # ── Build feature vector ──────────────────────────────────────────
        features = build_feature_vector(ratios, normalized_data)

        # ── Score with ML models ──────────────────────────────────────────
        scorer = RiskScorer()
        score_result = scorer.predict(features)

        logger.info(
            "risk_scored",
            filing_id=filing_id,
            score=score_result["risk_score"],
            risk_class=score_result["risk_class"],
        )

        # ── SHAP explanation ──────────────────────────────────────────────
        xgb_model = scorer._xgb_model  # already loaded
        explainer = SHAPExplainer(xgb_model)
        shap_result = explainer.explain(features)

        # ── Llama 3 narrative ─────────────────────────────────────────────
        company_name = filing.company.name if filing.company else "the company"
        narrative = generate_risk_narrative(
            risk_score=score_result["risk_score"],
            risk_class=score_result["risk_class"],
            top_factors=shap_result["top_factors"],
            company_name=company_name,
        )

        # ── Save to DB ────────────────────────────────────────────────────
        prediction = RiskPrediction(
            filing_id=filing_id,
            risk_score=score_result["risk_score"],
            risk_class=RiskClass(score_result["risk_class"]),
            xgb_score=score_result["xgb_score"],
            lgbm_score=score_result["lgbm_score"],
            xgb_weight=0.6,
            lgbm_weight=0.4,
            feature_vector=features,
            shap_values=shap_result["shap_values"],
            shap_base_value=shap_result["base_value"],
            top_factors=shap_result["top_factors"],
            narrative=narrative,
            narrative_model=settings_model(),
            model_version=MODEL_VERSION,
        )

        saved = self.risk_repo.save(prediction)

        logger.info("risk_prediction_saved", filing_id=filing_id,
                   prediction_id=str(saved.id))

        return saved

    def get_prediction(self, filing_id: str) -> RiskPrediction:
        """Get existing prediction or run it if not done yet."""
        prediction = self.risk_repo.get_by_filing_id(filing_id)
        if not prediction:
            prediction = self.run_risk_prediction(filing_id)
        return prediction


def settings_model() -> str:
    from app.core.config import settings
    return settings.OLLAMA_MODEL