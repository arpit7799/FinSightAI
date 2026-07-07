from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class NLPAnalysisResponse(BaseModel):

    id: int

    report_id: int

    tokens: list[str]

    lemmas: list[str]

    named_entities: list[dict]

    financial_keywords: list[str]

    processed_sentences: list[str]

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )