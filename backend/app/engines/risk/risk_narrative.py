# app/engines/risk/risk_narrative.py
"""
Generates a natural language risk narrative using Llama 3.

Takes the risk score, class, and top SHAP factors
and asks Llama 3 to write a concise risk summary
a credit officer or analyst would actually read.
"""

import httpx
from app.core.config import settings


def generate_risk_narrative(
    risk_score: float,
    risk_class: str,
    top_factors: list[dict],
    company_name: str = "the company",
) -> str:
    """
    Call Llama 3 to generate a risk narrative.

    If Ollama is not running, returns a template-based fallback
    so the rest of the pipeline doesn't break.

    Returns a plain string narrative.
    """

    # Build a clean summary of factors for the prompt
    factors_text = ""
    for i, factor in enumerate(top_factors[:3], 1):
        direction = "increases" if factor["direction"] == "increases_risk" else "decreases"
        factors_text += f"{i}. {factor['factor']} = {factor['feature_value']:.2f} ({direction} risk)\n"

    prompt = f"""You are a financial risk analyst. Write a concise 3-sentence risk assessment.

Company risk score: {risk_score:.1f}/100 ({risk_class} risk)

Top contributing factors:
{factors_text}

Write a professional risk summary for a credit officer. Be specific about the factors.
Do not use bullet points. Keep it under 100 words."""

    try:
        response = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 200,
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    except Exception:
        # Fallback narrative if Ollama is not running
        factor_names = [f["factor"] for f in top_factors[:3]]
        return (
            f"{company_name} has a risk score of {risk_score:.1f}/100, "
            f"classified as {risk_class} risk. "
            f"The primary risk drivers are: {', '.join(factor_names)}. "
            f"This assessment is based on ML analysis of 8 financial indicators."
        )