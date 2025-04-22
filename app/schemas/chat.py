from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class ChatMessage(BaseModel):
    role: str = Field(..., description="The role of the message sender (user/assistant)")
    content: str = Field(..., description="The content of the message")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="When the message was sent")

class ChatSession(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the chat session")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="When the session was created")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity timestamp")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message")
    session_id: Optional[str] = Field(None, description="Session identifier for continuing conversations")

class ChatResponse(BaseModel):
    message: str = Field(..., description="The assistant's response")
    session_id: str = Field(..., description="Session identifier for continuing the conversation")
    collected_fields: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Fields collected during the conversation"
    )
    is_complete: bool = Field(
        default=False,
        description="Whether all required fields have been collected"
    )

class ChatHistory(BaseModel):
    messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")
    collected_fields: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Fields collected during the conversation"
    )
    is_complete: bool = Field(
        default=False,
        description="Whether all required fields have been collected"
    ) 