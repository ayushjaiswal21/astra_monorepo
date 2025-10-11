from pydantic import BaseModel, field_validator
from typing import Optional
import re

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 5000:  # Limit message length
            raise ValueError('Message too long (max 5000 characters)')
        # Remove potentially dangerous characters
        v = re.sub(r'[<>"\\]', '', v.strip()) # Corrected escaping for backslash
        return v
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError('Invalid session ID format')
        return v

class ImageRequest(BaseModel):
    description: str
    session_id: Optional[str] = None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if len(v) > 1000:
            raise ValueError('Description too long (max 1000 characters)')
        v = re.sub(r'[<>"\\]', '', v.strip()) # Corrected escaping for backslash
        return v

class FeedbackRequest(BaseModel):
    interaction_id: str
    session_id: str
    feedback_type: str
    feedback_text: Optional[str] = None
    
    @field_validator('feedback_type')
    @classmethod
    def validate_feedback_type(cls, v):
        allowed_types = ['thumbs_up', 'thumbs_down', 'format_mismatch', 'too_long', 'too_short', 'off_topic']
        if v not in allowed_types:
            raise ValueError(f'Invalid feedback type. Must be one of: {allowed_types}')
        return v
