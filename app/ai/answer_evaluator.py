import json
from app.ai.client import get_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SKIP_PHRASES = {"skip", "idk", "i don't know", "i dont know", "next", "pass", "no idea"}


def evaluate_answer(
    question: str,
    answer: str,
    candidate_name: str,
    experience_level: str,
    tech_stack: str,
) -> dict:
    """Evaluate an answer and return score (0-10), feedback, explanation, key points."""
    if any(phrase in answer.lower() for phrase in _SKIP_PHRASES):
        return {
            "score": 0,
            "feedback": f"No worries, {candidate_name}! We'll skip that one.",
            "explanation": "This question was skipped.",
            "key_points_covered": [],
            "missing_points": [],
            "skipped": True,
        }

    try:
        client = get_client()
        prompt = (
            f"You are a strict but encouraging technical interviewer evaluating a "
            f"{experience_level} {tech_stack} candidate named {candidate_name}.\n\n"
            f"Question: \"{question}\"\n"
            f"Answer: \"{answer}\"\n\n"
            "Evaluate the answer and return ONLY valid JSON:\n"
            "{\n"
            "  \"score\": <integer 0-10>,\n"
            "  \"feedback\": \"<1-2 sentence personalised feedback using candidate name>\",\n"
            "  \"explanation\": \"<correct/complete answer starting with 'Here is the breakdown:'>\",\n"
            "  \"key_points_covered\": [\"point1\"],\n"
            "  \"missing_points\": [\"point1\"]\n"
            "}\n\n"
            "Scoring: 9-10 Excellent | 7-8 Good | 5-6 Partial | 3-4 Basic | 1-2 Attempted | 0 Irrelevant"
        )
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            max_tokens=700,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        result["skipped"] = False
        result.setdefault("score", 5)
        return result
    except Exception as exc:
        logger.error(f"Answer evaluation error: {exc}")
        return {
            "score": 5,
            "feedback": f"Thanks for your answer, {candidate_name}!",
            "explanation": "Let's move on.",
            "key_points_covered": [],
            "missing_points": [],
            "skipped": False,
        }
