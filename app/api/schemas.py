from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union

class ChatMessage(BaseModel):
    role: str = Field(..., description="The role of the message sender (user or assistant)")
    content: str = Field(..., description="The content of the message")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message to the chatbot")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None, 
        description="Previous conversation messages for context"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "message": "I'm looking for an apartment in New York with a budget of $500,000",
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help you with your real estate needs today?"}
                ]
            }
        }

class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant's response to the user")
    collected_fields: Dict[str, Optional[str]] = Field(
        ..., 
        description="Fields collected from the conversation (budget, total_size, property_type, city, etc.)"
    )
    is_complete: bool = Field(..., description="Whether all required fields have been collected")
    
    class Config:
        schema_extra = {
            "example": {
                "response": "I understand you're looking for an apartment in New York with a budget of $500,000. What size are you looking for?",
                "collected_fields": {
                    "budget": "500000",
                    "property_type": "apartment",
                    "city": "New York",
                    "total_size": None
                },
                "is_complete": False
            }
        }

class RealEstateRequirements(BaseModel):
    budget: Optional[str] = Field(None, description="The user's budget for the property")
    total_size: Optional[str] = Field(None, description="The required total size of the property")
    property_type: Optional[str] = Field(None, description="The type of property (apartment, house, commercial)")
    city: Optional[str] = Field(None, description="The city where the property is located")
    additional_fields: Optional[Dict[str, str]] = Field(None, description="Any additional requirements specified by the user")
    
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
                }
            }
        } 