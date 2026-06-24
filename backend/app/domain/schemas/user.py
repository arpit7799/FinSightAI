from uuid import UUID

from pydantic import BaseModel

from app.domain.models.enums import UserRole


class UserResponse(BaseModel):

    id: UUID
    email: str
    full_name: str
    role: UserRole

    model_config = {
        "from_attributes": True
    }