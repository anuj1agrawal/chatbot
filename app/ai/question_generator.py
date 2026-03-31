import json
from app.ai.client import get_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

_FALLBACK = [
    {"question": "Explain the importance of code readability and maintainability.", "difficulty": "easy"},
    {"question": "How do you approach debugging a complex issue in production?", "difficulty": "medium"},
    {"question": "Describe the SOLID principles and give an example for each.", "difficulty": "medium"},
    {"question": "What are the trade-offs between SQL and NoSQL databases?", "difficulty": "medium"},
    {"question": "How do you design a system for high availability and fault tolerance?", "difficulty": "hard"},
]


def _difficulty_plan(experience: float) -> list[str]:
    if experience < 2:
        return ["easy", "easy", "medium", "medium", "medium"]
    if experience < 5:
        return ["medium", "medium", "medium", "hard", "hard"]
    return ["medium", "hard", "hard", "hard", "hard"]


def _experience_label(experience: float) -> str:
    if experience < 2:
        return "entry-level"
    if experience < 5:
        return "mid-level"
    return "senior-level"


def generate_questions(
    tech_stack: str, experience: float, position: str, num_questions: int = 5
) -> list[dict]:
    """Return a list of {question, difficulty} dicts tailored to the candidate."""
    plan = _difficulty_plan(experience)
    level = _experience_label(experience)

    try:
        client = get_client()
        prompt = (
            f"Generate exactly {num_questions} technical interview questions for a "
            f"{level} {position} candidate whose tech stack is: {tech_stack}.\n"
            f"Experience: {experience} years.\n"
            f"Difficulty distribution required: {', '.join(plan)}.\n"
            "Requirements:\n"
            "- Test conceptual understanding, design patterns, and problem-solving.\n"
            "- Be specific to the stated tech stack.\n"
            "- No questions requiring multi-line code as an answer.\n"
            "- Each question must be clear and concise (one sentence).\n\n"
            f"Return a JSON object: {{\"questions\": ["
            "{\"question\": \"...\", \"difficulty\": \"easy|medium|hard\"}, ...]}"
        )
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            max_tokens=900,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        items = parsed.get("questions", parsed) if isinstance(parsed, dict) else parsed
        if isinstance(items, list) and len(items) >= num_questions:
            return [
                {"question": q["question"], "difficulty": q.get("difficulty", "medium")}
                for q in items[:num_questions]
            ]
    except Exception as exc:
        logger.error(f"Question generation failed: {exc}")

    return _FALLBACK[:num_questions]


def generate_followup(original_question: str, answer: str) -> str | None:
    """Return a single follow-up question or None if not needed."""
    try:
        client = get_client()
        prompt = (
            f"Interviewer asked: {original_question}\n"
            f"Candidate answered: {answer}\n\n"
            "If the answer is incomplete or reveals a knowledge gap worth probing, "
            "write ONE concise follow-up question. Otherwise return null.\n"
            "Return JSON: {\"followup\": \"question or null\"}"
        )
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            max_tokens=120,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        fu = result.get("followup")
        return fu if fu and str(fu).lower() != "null" else None
    except Exception:
        return None
