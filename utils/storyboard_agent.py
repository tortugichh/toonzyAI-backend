from schemas.storyboard_schemas import StoryboardCreateRequest, StoryboardResponse, StoryboardFrame
import uuid
import os
from utils.model_manager import generate_image
import logging
from moviepy.editor import ImageSequenceClip

STORYBOARD_DIR = "static/storyboards"
os.makedirs(STORYBOARD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)

async def generate_storyboard(request: StoryboardCreateRequest) -> StoryboardResponse:
    frames = []
    frame_paths = []
    try:
        for i in range(request.num_frames):
            frame_id = str(uuid.uuid4())
            # Можно модифицировать prompt для разнообразия кадров
            frame_prompt = f"{request.prompt}, frame {i+1}"  # или добавить эмоции/действия
            image_bytes, _ = generate_image(frame_prompt)
            image_path = os.path.join(STORYBOARD_DIR, f"{request.avatar_id}_frame_{i}.png")
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            image_url = f"/static/storyboards/{request.avatar_id}_frame_{i}.png"
            frames.append(StoryboardFrame(frame_id=frame_id, image_url=image_url))
            frame_paths.append(image_path)
        # Собираем MP4
        mp4_filename = f"{request.avatar_id}_storyboard.mp4"
        mp4_path = os.path.join(STORYBOARD_DIR, mp4_filename)
        clip = ImageSequenceClip(frame_paths, fps=2)
        clip.write_videofile(mp4_path, codec="libx264", audio=False, verbose=False, logger=None)
        mp4_url = f"/static/storyboards/{mp4_filename}"
        logger.info(f"Storyboard generated: {len(frames)} frames, mp4: {mp4_url}")
        return StoryboardResponse(frames=frames, mp4_url=mp4_url)
    except Exception as e:
        logger.error(f"Failed to generate storyboard: {e}")
        raise 