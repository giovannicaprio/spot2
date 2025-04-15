from pydantic import BaseModel
from typing import List, Optional, Dict, Union

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    response: str
    collected_fields: Dict[str, Optional[str]]
    is_complete: bool

class RealEstateRequirements(BaseModel):
    budget: Optional[str] = None
    total_size: Optional[str] = None
    property_type: Optional[str] = None
    city: Optional[str] = None
    additional_fields: Optional[Dict[str, str]] = None 