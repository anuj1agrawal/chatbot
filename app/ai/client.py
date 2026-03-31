import os
from groq import Groq
from app.utils.logger import get_logger
from app.utils.errors import AIError

logger = get_logger(__name__)
_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise AIError("GROQ_API_KEY not configured")
        _client = Groq(api_key=api_key)
        logger.info("Groq AI client initialised")
    return _client
