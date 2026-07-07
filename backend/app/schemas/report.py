from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class ReportResponse(BaseModel):

    id: int

    company_id: int

    original_filename: str

    stored_filename: str

    file_type: str

    file_size: int

    upload_date: datetime

    model_config = ConfigDict(
        from_attributes=True
    )