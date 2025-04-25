from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

class CollectedInfo(BaseModel):
    budget: Optional[str] = Field(None, description="The user's budget for the property")
    total_size: Optional[str] = Field(None, description="The required total size of the property")
    property_type: Optional[str] = Field(None, description="The type of property")
    city: Optional[str] = Field(None, description="The city where the property is located")
    additional_fields: Optional[Dict[str, str]] = Field(default_factory=dict, description="Any additional requirements")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the information was collected")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the information was last updated")
    conversation_id: Optional[str] = Field(None, description="Unique identifier for the conversation")
    
    class Config:
        schema_extra = {
            "example": {
                "budget": "500000",
                "total_size": "100",
                "property_type": "apartment",
                "city": "New York",
                "additional_fields": {
                    "bedrooms": "2",
                    "bathrooms": "1"
                },
                "created_at": "2024-03-20T10:00:00Z",
                "updated_at": "2024-03-20T10:00:00Z",
                "conversation_id": "conv_123"
            }
        } 