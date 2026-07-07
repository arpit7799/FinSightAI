from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class ExtractedTextResponse(BaseModel):

    id: int

    report_id: int

    extracted_text: str

    extraction_date: datetime

    model_config = ConfigDict(
        from_attributes=True
    )