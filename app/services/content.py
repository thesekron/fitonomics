from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
WORKOUTS_PATH = ROOT / "data" / "workouts_sample.json"
MEDIA_DIR = ROOT / "media" / "workouts"

logger = logging.getLogger(__name__)


def load_workouts(group: str) -> List[Dict]:
    """Load workouts list for a group; tolerate missing file/invalid JSON."""
    if not WORKOUTS_PATH.exists():
        logger.warning("Workouts JSON not found at %s", WORKOUTS_PATH)
        return []
    try:
        with open(WORKOUTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get(group, []) if isinstance(data, dict) else []
        return items if isinstance(items, list) else []
    except Exception as exc:
        logger.exception("Failed to load workouts JSON: %s", exc)
        return []


def get_workout_media_path(filename: Optional[str]) -> Optional[Path]:
    """Resolve media path for a workout GIF; return None if missing or invalid."""
    if not filename:
        return None
    try:
        path = MEDIA_DIR / filename
        if path.exists() and path.is_file():
            return path
        logger.info("Workout media not found: %s", path)
        return None
    except Exception as exc:
        logger.exception("Error resolving media path for %s: %s", filename, exc)
        return None