from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from uuid import UUID

class StoryCreateRequest(BaseModel):
    """Request body when user wants to create a new story."""
    prompt: str = Field(..., description="High-level idea or prompt from the user")


class StoryStatusResponse(BaseModel):
    """Generic status response for a Celery task."""
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Current task status (PENDING | STARTED | SUCCESS | FAILURE)")
    error: Optional[str] = Field(None, description="Error message in case of failure")


class StoryResultResponse(BaseModel):
    """Response returned when story generation completed successfully."""
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="SUCCESS if completed")

    # Agent outputs
    script: Dict[str, Any]
    style: Dict[str, Any]
    characters: Dict[str, Any]
    environments: Dict[str, Any] 