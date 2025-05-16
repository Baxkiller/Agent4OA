from pydantic import BaseModel, Field
from typing import Optional

class Preference(BaseModel):
    user_id: str = Field(..., description="用户ID")
    preference_type: str = Field(..., description="偏好类型，如 app_usage, interest 等")
    preference_value: str = Field(..., description="偏好值") 