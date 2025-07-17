from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

class CharacterInput(BaseModel):
    name: str
    description: Optional[str] = None
    role: Optional[str] = None

class StoryCreateRequest(BaseModel):
    """Request body when user wants to create a new story (structured)."""
    prompt: Optional[str] = Field(None, description="High-level idea or prompt from the user (for backward compatibility)")
    genre: Optional[str] = Field(None, description="Genre of the story (fairy tale, sci-fi, etc.)")
    style: Optional[str] = Field(None, description="Style or mood (funny, magical, dark, etc.)")
    theme: Optional[str] = Field(None, description="Main theme or topic of the story")
    book_style: Optional[str] = Field(None, description="Book visual style (colorful, vintage, etc.)")
    characters: Optional[List[CharacterInput]] = Field(default_factory=list, description="List of characters")
    wishes: Optional[str] = Field(None, description="Special wishes or requirements for the story")


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
    illustrations: Dict[str, Any]


class StoryItemResponse(BaseModel):
    """Individual story item in list response."""
    id: UUID = Field(..., description="Story ID")
    title: str = Field(..., description="Story title")
    theme: Optional[str] = Field(None, description="Story theme")
    genre: Optional[str] = Field(None, description="Story genre")
    style: Optional[str] = Field(None, description="Story style")
    status: str = Field(..., description="Generation status")
    preview_text: Optional[str] = Field(None, description="Preview text from first page")
    created_at: datetime = Field(..., description="Creation timestamp")
    task_id: str = Field(..., description="Celery task ID")


class StoryListResponse(BaseModel):
    """Response for list of user stories."""
    stories: List[StoryItemResponse] = Field(..., description="List of stories") 