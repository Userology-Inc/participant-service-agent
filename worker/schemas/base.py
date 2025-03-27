#!/usr/bin/env python3
"""
Base schemas and type definitions for the participant service agent.
"""

from typing import Dict, List, Optional, Any, Union, TypedDict
from dataclasses import dataclass
from datetime import datetime
import uuid

# Common ID type
ID = str

@dataclass
class BaseModel:
    """Base class for all data models."""
    id: ID
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def create(cls, **kwargs) -> 'BaseModel':
        """Create a new instance with default values for id and timestamps."""
        now = datetime.utcnow()
        return cls(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **kwargs
        )

class ApiResponse(TypedDict):
    """Standard API response format."""
    success: bool
    data: Optional[Any]
    error: Optional[str]

# Common result types
Result = Union[Any, Exception]

def success_response(data: Any = None) -> ApiResponse:
    """Create a success response."""
    return {"success": True, "data": data, "error": None}

def error_response(error: str) -> ApiResponse:
    """Create an error response."""
    return {"success": False, "data": None, "error": error} 