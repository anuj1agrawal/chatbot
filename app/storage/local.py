"""
Local file-based storage for interview data.
Stores each interview as a JSON file in data/interviews/ folder.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Data directory
DATA_DIR = Path("data") / "interviews"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_interview(candidate_data: dict, questions: list, answers: list, scores: list, summary: dict) -> str:
    """
    Save complete interview to a JSON file.
    Returns the interview ID (filename).
    """
    interview_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = DATA_DIR / f"{interview_id}.json"

    data = {
        "interview_id": interview_id,
        "timestamp": datetime.now().isoformat(),
        "candidate": candidate_data,
        "questions": questions,
        "answers": answers,
        "scores": scores,
        "summary": summary,
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Interview saved: {interview_id}")
        return interview_id
    except Exception as e:
        logger.error(f"Failed to save interview: {e}")
        raise


def get_all_interviews() -> list[dict]:
    """Retrieve all past interviews."""
    interviews = []
    try:
        for filepath in sorted(DATA_DIR.glob("*.json"), reverse=True):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                interviews.append(data)
    except Exception as e:
        logger.error(f"Failed to retrieve interviews: {e}")
    return interviews


def get_interview(interview_id: str) -> dict | None:
    """Retrieve a specific interview by ID."""
    filepath = DATA_DIR / f"{interview_id}.json"
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to retrieve interview {interview_id}: {e}")
    return None


def cleanup_old_interviews(days: int = 30) -> int:
    """Delete interviews older than N days. Returns count deleted."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0
    try:
        for filepath in DATA_DIR.glob("*.json"):
            file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
            if file_time < cutoff:
                filepath.unlink()
                deleted += 1
                logger.info(f"Deleted old interview: {filepath.name}")
    except Exception as e:
        logger.error(f"Failed to cleanup interviews: {e}")
    return deleted
