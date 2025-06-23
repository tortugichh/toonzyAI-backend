from fastapi import APIRouter
from schemas.storyboard_schemas import StoryboardCreateRequest, StoryboardResponse
from utils.storyboard_agent import generate_storyboard

router = APIRouter()

@router.post("/storyboard/", response_model=StoryboardResponse)
async def create_storyboard(request: StoryboardCreateRequest) -> StoryboardResponse:
    return await generate_storyboard(request) 