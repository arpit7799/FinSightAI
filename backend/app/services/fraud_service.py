# app/services/fraud_service.py
"""
Orchestrates the full fraud detection pipeline.

Steps:
1. Load normalized financial data from DB
2. Run Beneish M-Score
3. Run Altman Z-Score
4. Run Isolation Forest (needs ratio features from Phase 7)
5. Compute composite fraud score
6. Generate Llama 3 narrative
7. Save to DB
"""

import structlog
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.domain.models.fraud_assessment import FraudAssessment
from app.domain.models.enums import FraudRiskClass, AltmanZone
from app.engines.fraud.beneish_calculator import calculate_beneish
from app.engines.fraud.altman_calculator import calculate_altman
from app.engines.fraud.isolation_forest_detector import IsolationForestDetector
from app.engines.fraud.fraud_aggregator import (
    compute_composite_fraud_score,
    get_fraud_risk_class,
    merge_red_flags,
)
from app.repositories.filing_repository import FilingRepository
from app.repositories.statement_repository import StatementRepository
from app.repositories.ratio_repository import RatioRepository
from app.repositories.fraud_repository import FraudRepository
from app.engines.risk.feature_engineer import build_feature_vector

logger = structlog.get_logger()

MODEL_VERSION = "v1.0"


class FraudService:

    def __init__(self, db: Session):
        self.db = db
        self.filing_repo   = FilingRepository(db)
        self.statement_repo = StatementRepository(db)
        self.ratio_repo    = RatioRepository(db)
        self.fraud_repo    = FraudRepository(db)

    def run_fraud_detection(self, filing_id: str) -> FraudAssessment:
        """
        Run the full fraud detection pipeline for a filing.
        Returns the saved FraudAssessment record.
        """
        # ── Validate filing ───────────────────────────────────────────────
        filing = self.filing_repo.get_by_id(filing_id)
        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")

        # ── Load financial data ───────────────────────────────────────────
        normalized_data = self.statement_repo.get_normalized_data(filing_id)
        if not normalized_data:
            raise HTTPException(
                status_code=422,
                detail="No financial data found. Run document processing first.",
            )

        logger.info("fraud_detection_started", filing_id=filing_id)

        # ── Beneish M-Score ───────────────────────────────────────────────
        beneish_result = calculate_beneish(current=normalized_data)

        logger.info(
            "beneish_calculated",
            filing_id=filing_id,
            score=beneish_result["beneish_score"],
            signal=beneish_result["beneish_signal"],
        )

        # ── Altman Z-Score ────────────────────────────────────────────────
        altman_result = calculate_altman(normalized_data)

        logger.info(
            "altman_calculated",
            filing_id=filing_id,
            score=altman_result["altman_score"],
            zone=altman_result["altman_zone"],
        )

        # ── Isolation Forest ──────────────────────────────────────────────
        ratios = self.ratio_repo.get_by_filing_id(filing_id)
        features = build_feature_vector(ratios, normalized_data)

        detector = IsolationForestDetector()
        isolation_result = detector.detect(features)

        logger.info(
            "isolation_forest_run",
            filing_id=filing_id,
            is_anomaly=isolation_result["is_anomaly"],
            score=isolation_result["isolation_score"],
        )

        # ── Composite fraud score ─────────────────────────────────────────
        composite_score = compute_composite_fraud_score(
            beneish_signal=beneish_result["beneish_signal"],
            altman_zone=altman_result["altman_zone"],
            is_anomaly=isolation_result["is_anomaly"],
        )

        fraud_class = get_fraud_risk_class(composite_score)

        # ── Merge all red flags ───────────────────────────────────────────
        all_red_flags = merge_red_flags(
            beneish_flags=beneish_result["red_flags"],
            altman_flags=altman_result["red_flags"],
            isolation_flags=isolation_result["red_flags"],
        )

        # ── Generate Llama 3 narrative ────────────────────────────────────
        narrative = self._generate_narrative(
            filing=filing,
            beneish_score=beneish_result["beneish_score"],
            beneish_signal=beneish_result["beneish_signal"],
            altman_score=altman_result["altman_score"],
            altman_zone=altman_result["altman_zone"],
            composite_score=composite_score,
            fraud_class=fraud_class,
            red_flags=all_red_flags,
        )

        # ── Save to DB ────────────────────────────────────────────────────
        assessment = FraudAssessment(
            filing_id=filing_id,
            # Beneish variables
            dsri=beneish_result["dsri"],
            gmi=beneish_result["gmi"],
            aqi=beneish_result["aqi"],
            sgi=beneish_result["sgi"],
            depi=beneish_result["depi"],
            sgai=beneish_result["sgai"],
            lvgi=beneish_result["lvgi"],
            tata=beneish_result["tata"],
            beneish_score=beneish_result["beneish_score"],
            beneish_signal=FraudRiskClass(beneish_result["beneish_signal"]),
            # Altman variables
            altman_x1=altman_result["altman_x1"],
            altman_x2=altman_result["altman_x2"],
            altman_x3=altman_result["altman_x3"],
            altman_x4=altman_result["altman_x4"],
            altman_x5=altman_result["altman_x5"],
            altman_score=altman_result["altman_score"],
            altman_zone=AltmanZone(altman_result["altman_zone"]),
            # Isolation Forest
            isolation_score=isolation_result["isolation_score"],
            is_anomaly=isolation_result["is_anomaly"],
            # Aggregated
            overall_fraud_score=composite_score,
            fraud_risk_class=FraudRiskClass(fraud_class),
            red_flags=all_red_flags,
            narrative=narrative,
            model_version=MODEL_VERSION,
        )

        saved = self.fraud_repo.save(assessment)

        logger.info(
            "fraud_detection_complete",
            filing_id=filing_id,
            composite_score=composite_score,
            fraud_class=fraud_class,
            red_flag_count=len(all_red_flags),
        )

        return saved

    def get_assessment(self, filing_id: str) -> FraudAssessment:
        """Get existing assessment or run detection if not done yet."""
        assessment = self.fraud_repo.get_by_filing_id(filing_id)
        if not assessment:
            assessment = self.run_fraud_detection(filing_id)
        return assessment

    def _generate_narrative(self, filing, **kwargs) -> str:
        """Generate Llama 3 fraud narrative. Falls back to template if Ollama unavailable."""
        company_name = filing.company.name if filing.company else "the company"

        red_flag_count = len(kwargs.get("red_flags", []))
        high_flags = [f for f in kwargs.get("red_flags", []) if f.get("severity") == "HIGH"]

        prompt = f"""You are a forensic accountant. Write a concise 3-sentence fraud risk assessment.

Company: {company_name}
Beneish M-Score: {kwargs['beneish_score']:.3f} ({kwargs['beneish_signal']})
Altman Z-Score: {kwargs['altman_score']:.3f} ({kwargs['altman_zone']} zone)
Composite Fraud Score: {kwargs['composite_score']:.1f}/100 ({kwargs['fraud_class']})
Red Flags Triggered: {red_flag_count} total, {len(high_flags)} HIGH severity

Write a professional fraud risk summary for an auditor. Be specific. Under 100 words."""

        try:
            import httpx
            response = httpx.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 200},
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception:
            # Template fallback
            return (
                f"{company_name} has a fraud risk score of {kwargs['composite_score']:.1f}/100 "
                f"({kwargs['fraud_class']}). "
                f"Beneish M-Score of {kwargs['beneish_score']:.3f} signals {kwargs['beneish_signal'].lower().replace('_', ' ')}, "
                f"and Altman Z-Score of {kwargs['altman_score']:.3f} places the company in the {kwargs['altman_zone'].lower()} zone. "
                f"{red_flag_count} red flag(s) were identified requiring further review."
            )