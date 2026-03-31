import json
from app.ai.client import get_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _grade(pct: float) -> str:
    if pct >= 90: return "A"
    if pct >= 75: return "B"
    if pct >= 60: return "C"
    if pct >= 40: return "D"
    return "F"


def generate_summary(
    candidate_name: str,
    position: str,
    tech_stack: str,
    experience: float,
    questions: list[str],
    answers: list[str],
    scores: list[float],
) -> dict:
    """Generate comprehensive interview summary with strengths and recommendations."""
    total = sum(scores)
    max_score = len(scores) * 10.0
    pct = (total / max_score * 100) if max_score else 0
    grade = _grade(pct)

    try:
        client = get_client()
        qa_block = "\n".join(
            [f"Q{i+1}: {q}\nAnswer: {a}\nScore: {s}/10"
             for i, (q, a, s) in enumerate(zip(questions, answers, scores))]
        )
        prompt = (
            f"You are a senior technical recruiter writing a post-interview evaluation.\n\n"
            f"Candidate: {candidate_name} | Position: {position}\n"
            f"Tech Stack: {tech_stack} | Experience: {experience} years\n"
            f"Score: {total}/{max_score} ({pct:.1f}%) — Grade: {grade}\n\n"
            f"Interview transcript:\n{qa_block}\n\n"
            "Write a professional evaluation as JSON:\n"
            "{\n"
            "  \"summary\": \"<2-3 paragraph balanced assessment>\",\n"
            "  \"strengths\": [\"s1\", \"s2\", \"s3\"],\n"
            "  \"improvements\": [\"i1\", \"i2\", \"i3\"],\n"
            "  \"recommendation\": \"strong_hire|hire|consider|no_hire\",\n"
            "  \"next_steps\": \"<what happens next>\"\n"
            "}"
        )
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            max_tokens=900,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
    except Exception as exc:
        logger.error(f"Summary generation failed: {exc}")
        result = {
            "summary": f"{candidate_name} completed the technical interview for {position}.",
            "strengths": ["Completed all questions", "Showed initiative"],
            "improvements": ["Continue practising technical concepts"],
            "recommendation": "consider",
            "next_steps": "The team will review your application and be in touch within 2-3 business days.",
        }

    result["grade"] = grade
    result["percentage"] = round(pct, 1)
    result["total_score"] = total
    result["max_score"] = max_score
    return result
