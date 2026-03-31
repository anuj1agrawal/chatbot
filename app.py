"""
TalentScout AI Interviewer — Streamlit Dashboard
Single-file entry point. Delegates all business logic to app/ modules.
"""
import json
import os
import re

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Local storage ─────────────────────────────────────────────────────────────
from app.storage.local import save_interview

# ── Groq client (lazy, cached) ───────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _groq_client():
    from app.ai.client import get_client
    return get_client()

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
PHASES = {
    "GREETING": "greeting",
    "DATA_COLLECTION": "data_collection",
    "DATA_CONFIRMATION": "data_confirmation",
    "TECHNICAL_QUESTIONS": "technical_questions",
    "ENDED": "ended",
}

EXIT_KEYWORDS = {
    "bye", "goodbye", "exit", "quit", "end", "stop",
    "finish", "done", "thanks", "thank you",
}

GRADE_CONFIG = {
    "A": {"color": "#28a745", "label": "Excellent", "emoji": "🏆"},
    "B": {"color": "#17a2b8", "label": "Good",      "emoji": "🌟"},
    "C": {"color": "#ffc107", "label": "Average",   "emoji": "👍"},
    "D": {"color": "#fd7e14", "label": "Below Avg", "emoji": "📚"},
    "F": {"color": "#dc3545", "label": "Needs Work", "emoji": "💪"},
}

RECOMMENDATION_LABELS = {
    "strong_hire": ("Strong Hire", "#28a745"),
    "hire":        ("Hire",        "#17a2b8"),
    "consider":    ("Consider",    "#ffc107"),
    "no_hire":     ("No Hire",     "#dc3545"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Input validation (AI-assisted for free-text fields)
# ─────────────────────────────────────────────────────────────────────────────
def _ai_validate(user_input: str, field_name: str) -> bool:
    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            messages=[{
                "role": "system",
                "content": (
                    f"Is '{user_input}' a plausible real-world '{field_name}'? "
                    "Respond with only 'yes' or 'no'."
                ),
            }],
            model="llama-3.1-8b-instant",
            max_tokens=5,
            temperature=0.0,
        )
        return "yes" in resp.choices[0].message.content.strip().lower()
    except Exception:
        return len(user_input.strip()) > 2


# ─────────────────────────────────────────────────────────────────────────────
# Input extractors — strip conversational preamble, return the clean value
# ─────────────────────────────────────────────────────────────────────────────
def _extract_name(raw: str) -> str:
    """'My name is Amit Kumar' → 'Amit Kumar'"""
    raw = raw.strip()
    m = re.search(
        r"(?:my name is|i am|i'm|im|call me|this is|name\s*[:\-]\s*)"
        r"\s*([a-zA-Z][a-zA-Z\s'\-]{0,49})",
        raw, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return raw


def _extract_email(raw: str) -> str:
    """'my email is amit@gmail.com' → 'amit@gmail.com'"""
    m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", raw)
    return m.group(0).strip() if m else raw.strip()


def _extract_phone(raw: str) -> str:
    """'my number is +91 98765 43210' → '+919876543210'"""
    raw = raw.strip()
    digits = re.sub(r"[^0-9]", "", raw)
    # keep leading + for international numbers
    return ("+" + digits) if raw.lstrip().startswith("+") and digits else digits if digits else raw


def _extract_experience(raw: str) -> str:
    """'I have 3.5 years of experience' → '3.5', 'fresher' → '0'"""
    lower = raw.lower()
    if re.search(r"\b(fresher|fresh graduate|no experience|zero|0 year|just started|just graduated|entry.?level)\b", lower):
        return "0"
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?|y\.?o\.?e\.?)?\b", raw, re.IGNORECASE)
    return m.group(1) if m else raw.strip()


def _extract_freetext(raw: str) -> str:
    """Strip common conversational lead-ins for position/location/tech-stack."""
    prefixes = [
        r"^i(?:'m| am) (?:applying for|looking for|interested in|seeking)\s+(?:a |an |the )?",
        r"^(?:i prefer|my preferred(?:\s+location)? is|i(?:'m| am) (?:based in|from|in|at))\s+",
        r"^(?:i(?:'m| am) (?:proficient in|skilled in|experienced(?:\s+in)?|good at|familiar with|working with))\s+",
        r"^(?:my (?:tech stack|skills?|technologies|expertise) (?:is|are|includes?)[:\s]+)\s*",
        r"^(?:position|role|job|location|tech|stack|skills?)\s*[:\-]\s*",
    ]
    result = raw.strip()
    for pat in prefixes:
        result = re.sub(pat, "", result, flags=re.IGNORECASE).strip()
    return result.strip("\"'").strip() or raw.strip()


def _is_fake_phone(digits: str) -> bool:
    """Return True if the digit string looks like a placeholder/fake number."""
    d = re.sub(r"[^0-9]", "", digits)
    if not d:
        return True
    # All same digit (e.g. 9999999999)
    if len(set(d)) == 1:
        return True
    # Classic sequential fillers
    _FAKES = {
        "1234567890", "0123456789", "9876543210", "0987654321",
        "1234567891", "12345678901", "123456789",
    }
    if d in _FAKES or d[:10] in _FAKES:
        return True
    # 7+ consecutive identical digits anywhere (e.g. 98111111112)
    if re.search(r"(.)\1{6,}", d):
        return True
    return False


DATA_STEPS = {
    1: {
        "field": "name",
        "prompt": "What is your full name?",
        "extractor": _extract_name,
        "validation": lambda x: (
            bool(re.match(r"^[a-zA-Z][a-zA-Z\s'\-]{1,49}$", x.strip()))
            and 2 <= len(x.strip()) <= 50
        ),
        "error": "Please share your name using letters only (e.g. Amit Kumar).",
    },
    2: {
        "field": "email",
        "prompt": "Could you share your email address?",
        "extractor": _extract_email,
        "validation": lambda x: (
            bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", x.strip()))
            and _ai_validate(x, "real personal or professional email address (not random characters or gibberish)")
        ),
        "error": "That doesn't look like a real email address. Please provide one you actually use, e.g. amit@gmail.com.",
    },
    3: {
        "field": "phone",
        "prompt": "What is your phone number?",
        "extractor": _extract_phone,
        "validation": lambda x: (
            bool(re.match(r"^\+?\d{10,15}$", re.sub(r"\s", "", x)))
            and not _is_fake_phone(x)
        ),
        "error": "Please provide your actual phone number (10–15 digits). Sequential or repeated digits like 1234567890 are not accepted.",
    },
    4: {
        "field": "experience",
        "prompt": "How many years of professional experience do you have?",
        "extractor": _extract_experience,
        "validation": lambda x: bool(re.match(r"^\d+(\.\d+)?$", x.strip()))
                                 and 0 <= float(x.strip()) <= 50,
        "error": "Please give a number for years of experience — e.g. 0 for fresher, 3, or 5.5.",
    },
    5: {
        "field": "position",
        "prompt": "What position are you applying for?",
        "extractor": _extract_freetext,
        "validation": lambda x: len(x.strip()) >= 2 and _ai_validate(x, "Job Position"),
        "error": "Please provide a recognisable job title, e.g. 'Backend Developer'.",
    },
    6: {
        "field": "location",
        "prompt": "What is your preferred work location? (city or 'remote')",
        "extractor": _extract_freetext,
        "validation": lambda x: len(x.strip()) >= 2 and _ai_validate(x, "Work Location"),
        "error": "Please provide a city name or type 'remote'.",
    },
    7: {
        "field": "tech_stack",
        "prompt": "What programming languages, frameworks, and technologies are you proficient in?",
        "extractor": _extract_freetext,
        "validation": lambda x: len(x.strip()) >= 2 and _ai_validate(x, "Technology Stack"),
        "error": "Please list at least one technology, e.g. 'Python, Django, PostgreSQL'.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Session state helpers
# ─────────────────────────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "page": "home",
        "phase": PHASES["GREETING"],
        "messages": [],
        "candidate": {
            "name": "", "email": "", "phone": "", "experience": "",
            "position": "", "location": "", "tech_stack": "",
        },
        "step": 1,
        "questions": [],          # list[dict] — {question, difficulty}
        "question_ids": [],       # DB IDs
        "q_index": 0,
        "evaluations": [],        # list[dict] from answer_evaluator
        "scores": [],             # list[float]
        "summary": None,          # dict from feedback_generator
        # DB IDs
        "user_id": None,
        "interview_id": None,
        "retry_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def _first_name(data: dict | None = None) -> str:
    """Safely extract first name from candidate data, fall back to 'there'."""
    if data is None:
        data = st.session_state.get("candidate", {})
    raw = data.get("name", "").strip()
    parts = raw.split()
    return parts[0] if parts else "there"


# ─────────────────────────────────────────────────────────────────────────────
# AI helpers
# ─────────────────────────────────────────────────────────────────────────────
def _get_ai_response(messages: list, system_prompt: str) -> str:
    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, *messages],
            model="llama-3.1-8b-instant",
            max_tokens=400,
            temperature=0.8,
        )
        return resp.choices[0].message.content
    except Exception:
        return "I am having a brief technical hiccup — could we try that again? 😊"


def _generate_questions() -> list[dict]:
    from app.ai.question_generator import generate_questions
    data = st.session_state.candidate
    return generate_questions(
        tech_stack=data["tech_stack"],
        experience=float(data["experience"]),
        position=data["position"],
    )


def _evaluate(question: str, answer: str) -> dict:
    from app.ai.answer_evaluator import evaluate_answer
    data = st.session_state.candidate
    exp = float(data["experience"])
    level = "entry-level" if exp < 2 else "mid-level" if exp < 5 else "senior-level"
    first = _first_name(data)
    return evaluate_answer(
        question=question,
        answer=answer,
        candidate_name=first,
        experience_level=level,
        tech_stack=data["tech_stack"],
    )


def _build_summary() -> dict:
    from app.ai.feedback_generator import generate_summary
    data = st.session_state.candidate
    qs = [q["question"] for q in st.session_state.questions]
    ans_texts = [e.get("_raw_answer", "") for e in st.session_state.evaluations]
    return generate_summary(
        candidate_name=data["name"],
        position=data["position"],
        tech_stack=data["tech_stack"],
        experience=float(data["experience"]),
        questions=qs,
        answers=ans_texts,
        scores=st.session_state.scores,
    )

# ────────────────────────────────────────────────────────────────────────────
# Global CSS — injected once at bootstrap
# ─────────────────────────────────────────────────────────────────────────────
def _inject_css():
    st.markdown(
        """
        <style>
        /* ── Base ── */
        [data-testid="stAppViewContainer"] > .main { background: #0d0d12 !important; }
        section[data-testid="stSidebar"] {
            background: #111118 !important;
            border-right: 1px solid #1e1e2a !important;
        }
        .block-container { padding-top: 1.75rem !important; }

        /* ── Hero (home) ── */
        .ts-hero {
            padding: 3.5rem 1rem 2.75rem;
            text-align: center;
            border-bottom: 1px solid #1e1e2a;
            margin-bottom: 2.5rem;
        }
        .ts-hero-label {
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #7c6cf5;
            font-weight: 600;
            margin-bottom: 0.8rem;
        }
        .ts-hero-title {
            font-size: 2.8rem;
            font-weight: 700;
            color: #e8e8f0;
            margin: 0 0 1rem;
            letter-spacing: -0.02em;
            line-height: 1.1;
        }
        .ts-hero-sub {
            font-size: 1.05rem;
            color: #8b8b9e;
            max-width: 480px;
            margin: 0 auto;
            line-height: 1.65;
        }

        /* ── Feature cards (home) ── */
        .ts-feat {
            background: #13131b;
            border: 1px solid #1e1e2a;
            border-radius: 10px;
            padding: 1.25rem;
            height: 100%;
        }
        .ts-feat-icon { font-size: 1.3rem; margin-bottom: 0.5rem; }
        .ts-feat-title {
            font-size: 0.88rem;
            font-weight: 600;
            color: #d0d0e0;
            margin: 0 0 0.3rem;
        }
        .ts-feat-text {
            font-size: 0.8rem;
            color: #7a7a8e;
            line-height: 1.55;
            margin: 0;
        }

        /* ── Page header (results / interview) ── */
        .ts-page-header {
            padding: 1.5rem 0 1.25rem;
            border-bottom: 1px solid #1e1e2a;
            margin-bottom: 1.75rem;
        }
        .ts-page-header h2 {
            font-size: 1.4rem;
            font-weight: 600;
            color: #e0e0ee;
            margin: 0 0 0.2rem;
        }
        .ts-page-header p { font-size: 0.85rem; color: #7a7a8e; margin: 0; }

        /* ── Chat page header ── */
        .ts-chat-header {
            padding: 0.75rem 0 0.75rem;
            border-bottom: 1px solid #1e1e2a;
            margin-bottom: 1rem;
        }
        .ts-chat-header h2 {
            font-size: 1.2rem;
            font-weight: 600;
            color: #e0e0ee;
            margin: 0 0 0.15rem;
        }
        .ts-chat-header p { font-size: 0.8rem; color: #7a7a8e; margin: 0; }

        /* ── Grade / recommendation badges (results) ── */
        .ts-badge-row {
            display: flex;
            gap: 1rem;
            margin: 1.25rem 0 1.75rem;
        }
        .ts-badge {
            background: #13131b;
            border: 1px solid #1e1e2a;
            border-radius: 10px;
            padding: 1rem 1.5rem;
            flex: 1;
            text-align: center;
        }
        .ts-badge-value { font-size: 1.9rem; font-weight: 700; margin: 0.2rem 0 0.15rem; }
        .ts-badge-label {
            font-size: 0.7rem;
            color: #5a5a6e;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.1rem;
        }
        .ts-badge-sub { font-size: 0.8rem; color: #7a7a8e; }

        /* ── Score breakdown (results) ── */
        .ts-qrow {
            padding: 0.9rem 0;
            border-bottom: 1px solid #181820;
        }
        .ts-qrow:last-child { border-bottom: none; }
        .ts-qtitle { font-size: 0.85rem; color: #c8c8d8; margin-bottom: 0.45rem; }
        .ts-qdiff {
            font-size: 0.68rem;
            background: #1e1e2a;
            color: #6a6a7e;
            border-radius: 3px;
            padding: 1px 5px;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-right: 5px;
        }
        .ts-sbar-track {
            background: #1a1a24;
            border-radius: 3px;
            height: 5px;
            margin: 0.45rem 0 0.3rem;
            overflow: hidden;
        }
        .ts-sbar-fill { height: 100%; border-radius: 3px; }
        .ts-score-val { font-size: 0.78rem; color: #6a6a7e; }

        /* ── Sidebar ── */
        .ts-sb-section {
            font-size: 0.68rem;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            color: #4a4a5e;
            font-weight: 600;
            margin: 1rem 0 0.4rem;
        }
        .ts-sb-kv { font-size: 0.8rem; color: #8a8a9e; margin: 0.18rem 0; }
        .ts-sb-kv b { color: #b8b8c8; }

        /* ── Misc ── */
        .stButton > button[kind="primary"] {
            background: #7c6cf5 !important;
            border: none !important;
            border-radius: 7px !important;
        }
        .stButton > button[kind="primary"]:hover {
            background: #6c5ce7 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: HOME
# ─────────────────────────────────────────────────────────────────────────────
def page_home():
    st.markdown(
        """
        <div class="ts-hero">
            <div class="ts-hero-label">AI Interview Platform</div>
            <h1 class="ts-hero-title">TalentScout</h1>
            <p class="ts-hero-sub">
                Skill-based technical interviews powered by AI —
                personalised questions, instant scoring, and a complete report.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """<div class="ts-feat">
                <div class="ts-feat-icon">◈</div>
                <div class="ts-feat-title">Smart Questions</div>
                <p class="ts-feat-text">Tailored to your tech stack and experience level — no generic tests.</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """<div class="ts-feat">
                <div class="ts-feat-icon">◉</div>
                <div class="ts-feat-title">Instant Scoring</div>
                <p class="ts-feat-text">Every answer scored 0–10 with AI feedback and correct explanation.</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """<div class="ts-feat">
                <div class="ts-feat-icon">◎</div>
                <div class="ts-feat-title">Full Report</div>
                <p class="ts-feat-text">Grade, strengths, improvement areas, and a hiring recommendation.</p>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([3, 2, 3])
    with col_btn:
        if st.button("Begin Interview", type="primary", use_container_width=True):
            st.session_state.page = "interview"
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: INTERVIEW — sidebar
# ─────────────────────────────────────────────────────────────────────────────
def _render_sidebar():
    with st.sidebar:
        st.markdown("<div class='ts-sb-section'>Progress</div>", unsafe_allow_html=True)

        phase = st.session_state.phase
        total_steps = len(DATA_STEPS)
        q_count = len(st.session_state.questions)
        q_idx = st.session_state.q_index

        if phase == PHASES["DATA_COLLECTION"]:
            pct = (st.session_state.step - 1) / total_steps * 0.65
        elif phase == PHASES["DATA_CONFIRMATION"]:
            pct = 0.70
        elif phase == PHASES["TECHNICAL_QUESTIONS"]:
            pct = 0.75 + (q_idx / q_count * 0.20) if q_count else 0.75
        elif phase == PHASES["ENDED"]:
            pct = 1.0
        else:
            pct = 0.0

        st.progress(pct)
        st.caption(phase.replace("_", " ").title())

        data = st.session_state.candidate
        if any(v for v in data.values()):
            st.markdown("<div class='ts-sb-section'>Candidate</div>", unsafe_allow_html=True)
            for key, val in data.items():
                if not val:
                    continue
                display = val
                if key == "email" and "@" in val:
                    local, domain = val.split("@", 1)
                    display = local[:2] + "·" * max(0, len(local) - 2) + "@" + domain
                elif key == "phone":
                    clean = re.sub(r"[^0-9]", "", val)
                    if len(clean) > 6:
                        display = clean[:3] + "···" + clean[-3:]
                label = key.replace("_", " ").title()
                st.markdown(
                    f"<div class='ts-sb-kv'><b>{label}</b>: {display}</div>",
                    unsafe_allow_html=True,
                )

        if st.session_state.questions and phase == PHASES["TECHNICAL_QUESTIONS"]:
            st.markdown("<div class='ts-sb-section'>Questions</div>", unsafe_allow_html=True)
            for i in range(len(st.session_state.questions)):
                if i < q_idx:
                    sc = st.session_state.scores[i] if i < len(st.session_state.scores) else 0
                    st.caption(f"Q{i+1}  ✓  {sc:.0f}/10")
                elif i == q_idx:
                    st.caption(f"Q{i+1}  →  active")
                else:
                    st.caption(f"Q{i+1}  ·  pending")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: INTERVIEW — main chat logic
# ─────────────────────────────────────────────────────────────────────────────
def page_interview():
    _render_sidebar()

    st.markdown(
        """
        <div class="ts-chat-header">
            <h2>Maya &nbsp;·&nbsp; Interview Assistant</h2>
            <p>Chat naturally — Maya will guide you through the interview.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Greet on first load
    if not st.session_state.messages and st.session_state.phase == PHASES["GREETING"]:
        greeting = _get_ai_response(
            [],
            "You are Maya, a friendly hiring assistant for TalentScout. "
            "Greet the candidate warmly, introduce yourself briefly, explain the process "
            "(collect info, then 5 technical questions, then results), "
            "and ask for their full name. Keep it concise and warm.",
        )
        st.session_state.messages.append({"role": "assistant", "content": greeting})
        st.session_state.phase = PHASES["DATA_COLLECTION"]
        st.rerun()

    if st.session_state.phase == PHASES["ENDED"]:
        # Render chat history then show the View Results button inline
        st.markdown("<br>", unsafe_allow_html=True)
        _, col_btn, _ = st.columns([2, 2, 2])
        with col_btn:
            if st.button("View Results", type="primary", use_container_width=True, key="top_view_results"):
                st.session_state.page = "results"
                st.rerun()
        return

    user_input = st.chat_input("Type your message here...")
    if not user_input:
        return

    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # ── Exit detection ───────────────────────────────────────────────────────
    if any(kw in user_input.lower() for kw in EXIT_KEYWORDS):
        name = _first_name()
        bot = f"Thank you for your time, {name}! Best of luck on your journey. 👋"
        st.session_state.messages.append({"role": "assistant", "content": bot})
        st.session_state.phase = PHASES["ENDED"]
        with st.chat_message("assistant"):
            st.markdown(bot)
        st.rerun()
        return

    phase = st.session_state.phase
    bot = ""
    data = st.session_state.candidate
    first = _first_name(data)

    # ── DATA COLLECTION ──────────────────────────────────────────────────────
    if phase == PHASES["DATA_COLLECTION"]:
        step = st.session_state.step
        step_cfg = DATA_STEPS[step]

        # Extract clean value from conversational input before validating
        extracted = step_cfg.get("extractor", lambda x: x.strip())(user_input)

        with st.spinner("Validating..."):
            is_valid = step_cfg["validation"](extracted)

        if is_valid:
            data[step_cfg["field"]] = extracted  # store clean extracted value, not raw
            st.session_state.step += 1

            if step == 1:
                first = _first_name(data)
                bot = (
                    f"Great to meet you, {first}! 😊 "
                    f"Next — {DATA_STEPS[2]['prompt']}"
                )
            elif step == 2:
                bot = f"Got it, {first}. Next — {DATA_STEPS[3]['prompt']}"
            elif step == 3:
                bot = f"Perfect, {first}. Next — {DATA_STEPS[4]['prompt']}"
            elif step == 4:
                exp = float(data["experience"])
                level_msg = (
                    "Just starting out — exciting!" if exp == 0
                    else f"{exp} years — great foundation!" if exp < 2
                    else f"{exp} years of solid experience!" if exp < 5
                    else f"{exp} years — impressive!"
                )
                bot = f"{level_msg} {DATA_STEPS[5]['prompt']}"
            elif step == 5:
                bot = (
                    f"A **{data['position']}** role — excellent choice! "
                    f"{DATA_STEPS[6]['prompt']}"
                )
            elif step == 6:
                bot = (
                    f"Location noted. Last one — {DATA_STEPS[7]['prompt']}"
                )

            if st.session_state.step > len(DATA_STEPS):
                st.session_state.phase = PHASES["DATA_CONFIRMATION"]
                summary_lines = "\n".join(
                    [f"- **{k.replace('_', ' ').title()}:** {v}"
                     for k, v in data.items() if v]
                )
                bot = (
                    f"Awesome, {first}! Here is a summary of your details:\n\n"
                    f"{summary_lines}\n\n"
                    "Does everything look correct? Type **yes** to proceed to the technical assessment, "
                    "or let me know what to change."
                )
        else:
            bot = f"Hmm, {first} — {step_cfg['error']} Could you try again? 😊"

    # ── DATA CONFIRMATION ────────────────────────────────────────────────────
    elif phase == PHASES["DATA_CONFIRMATION"]:
        if any(w in user_input.lower() for w in ("yes", "correct", "confirm", "ok", "proceed", "looks good")):
            with st.spinner("Generating personalised questions..."):
                questions = _generate_questions()

            st.session_state.questions = questions
            st.session_state.phase = PHASES["TECHNICAL_QUESTIONS"]

            q1 = questions[0]["question"]
            diff_badge = f"[{questions[0]['difficulty'].upper()}]"
            bot = (
                f"Excellent, {first}! I have prepared **{len(questions)} technical questions** "
                f"tailored to your {data['tech_stack']} expertise.\n\n"
                f"Each answer will be scored out of 10. Take your time!\n\n"
                f"---\n\n"
                f"**Question 1 of {len(questions)}** {diff_badge}\n\n{q1}"
            )
        else:
            bot = f"Of course, {first}! Which detail would you like to update?"

    # ── TECHNICAL QUESTIONS ──────────────────────────────────────────────────
    elif phase == PHASES["TECHNICAL_QUESTIONS"]:
        idx = st.session_state.q_index
        current_q = st.session_state.questions[idx]["question"]

        with st.spinner("Evaluating your answer..."):
            evaluation = _evaluate(current_q, user_input)

        evaluation["_raw_answer"] = user_input
        st.session_state.evaluations.append(evaluation)
        score = float(evaluation.get("score", 0))
        st.session_state.scores.append(score)

        feedback = evaluation.get("feedback", f"Thank you, {first}!")
        explanation = evaluation.get("explanation", "")
        score_bar = "🟩" * int(score) + "⬜" * (10 - int(score))

        bot = (
            f"{feedback}\n\n"
            f"**Score: {score:.0f}/10** {score_bar}\n\n"
            f"{explanation}"
        )

        st.session_state.q_index += 1

        if st.session_state.q_index < len(st.session_state.questions):
            nxt = st.session_state.questions[st.session_state.q_index]
            nq_text = nxt["question"]
            diff_badge = f"[{nxt['difficulty'].upper()}]"
            bot += (
                f"\n\n---\n\n"
                f"**Question {st.session_state.q_index + 1} of {len(st.session_state.questions)}**"
                f" {diff_badge}\n\n{nq_text}"
            )
        else:
            # All questions done — generate summary
            with st.spinner("Generating interview summary..."):
                summary = _build_summary()
            st.session_state.summary = summary
            
            # Save interview to local storage
            try:
                save_interview(
                    candidate_data=st.session_state.candidate,
                    questions=st.session_state.questions,
                    answers=[e.get("_raw_answer", "") for e in st.session_state.evaluations],
                    scores=st.session_state.scores,
                    summary=summary,
                )
            except Exception as e:
                st.warning(f"Could not save interview: {e}")

            grade = summary.get("grade", "?")
            pct = summary.get("percentage", 0)
            total = summary.get("total_score", 0)
            max_s = summary.get("max_score", 50)
            bot += (
                f"\n\n---\n\n"
                f"🎉 **Interview Complete, {first}!**\n\n"
                f"**Overall Score: {total:.0f}/{max_s:.0f} ({pct:.1f}%) — Grade {grade}**\n\n"
                f"Your detailed report is ready. Click the button below to view it!"
            )
            st.session_state.phase = PHASES["ENDED"]

    # ── Append and display bot response ─────────────────────────────────────
    if bot:
        st.session_state.messages.append({"role": "assistant", "content": bot})
        with st.chat_message("assistant"):
            st.markdown(bot)

    # Show "View Results" button inline (no rerun — avoids scroll-to-top)
    if st.session_state.phase == PHASES["ENDED"]:
        st.markdown("<br>", unsafe_allow_html=True)
        _, col_btn, _ = st.columns([2, 2, 2])
        with col_btn:
            if st.button("View Results", type="primary", use_container_width=True):
                st.session_state.page = "results"
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: RESULTS dashboard
# ─────────────────────────────────────────────────────────────────────────────
def page_results():
    # Scroll to top of page when results load
    st.components.v1.html(
        "<script>window.parent.document.querySelector('section.main').scrollTo(0, 0);</script>",
        height=0,
    )

    summary = st.session_state.get("summary")
    data = st.session_state.candidate
    scores = st.session_state.scores
    questions = st.session_state.questions
    evaluations = st.session_state.evaluations

    if not summary or not scores:
        st.warning("No interview results found. Please complete an interview first.")
        if st.button("Begin Interview"):
            st.session_state.page = "home"
            st.rerun()
        return

    grade = summary.get("grade", "F")
    g_cfg = GRADE_CONFIG.get(grade, GRADE_CONFIG["F"])
    pct = summary.get("percentage", 0)
    total = summary.get("total_score", 0)
    max_s = summary.get("max_score", 50)
    rec = summary.get("recommendation", "consider")
    rec_label, rec_color = RECOMMENDATION_LABELS.get(rec, ("Consider", "#ffc107"))

    # ── Header ──────────────────────────────────────────────────────────────
    name_disp = data.get("name", "Candidate")
    pos_disp = data.get("position", "")
    st.markdown(
        f"""
        <div class="ts-page-header">
            <h2>Interview Results</h2>
            <p>{name_disp}{" · " + pos_disp if pos_disp else ""}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Key metrics ──────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Score", f"{total:.0f} / {max_s:.0f}")
    m2.metric("Percentage", f"{pct:.1f}%")
    m3.metric("Grade", grade)
    m4.metric("Questions", f"{len(scores)} answered")

    # ── Grade + recommendation badges ────────────────────────────────────────
    st.markdown(
        f"""
        <div class="ts-badge-row">
            <div class="ts-badge">
                <div class="ts-badge-label">Grade</div>
                <div class="ts-badge-value" style="color:{g_cfg['color']};">{grade}</div>
                <div class="ts-badge-sub">{g_cfg['label']}</div>
            </div>
            <div class="ts-badge">
                <div class="ts-badge-label">Recommendation</div>
                <div class="ts-badge-value" style="color:{rec_color}; font-size:1.4rem;">{rec_label}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Score breakdown ──────────────────────────────────────────────────────
    st.markdown("#### Score Breakdown")
    score_html = ""
    for i, (q_obj, sc) in enumerate(zip(questions, scores)):
        colour = "#22c55e" if sc >= 7 else "#f59e0b" if sc >= 4 else "#ef4444"
        diff = q_obj.get("difficulty", "medium").upper()
        q_text = q_obj["question"][:85] + ("…" if len(q_obj["question"]) > 85 else "")
        fill_pct = sc / 10 * 100
        score_html += (
            f'<div class="ts-qrow">'
            f'<div class="ts-qtitle"><span class="ts-qdiff">{diff}</span>'
            f"Q{i + 1} &mdash; {q_text}</div>"
            f'<div class="ts-sbar-track">'
            f'<div class="ts-sbar-fill" style="width:{fill_pct:.0f}%;background:{colour};"></div>'
            f"</div>"
            f'<div class="ts-score-val">{sc:.1f} / 10</div>'
            f"</div>"
        )
    st.markdown(score_html, unsafe_allow_html=True)

    # ── Summary ──────────────────────────────────────────────────────────────
    with st.expander("Overall Assessment", expanded=True):
        st.markdown(summary.get("summary", ""))

    # ── Strengths & improvements ─────────────────────────────────────────────
    col_s, col_i = st.columns(2)
    strengths = summary.get("strengths", [])
    improvements = summary.get("improvements", [])
    if isinstance(strengths, str):
        strengths = json.loads(strengths)
    if isinstance(improvements, str):
        improvements = json.loads(improvements)

    with col_s:
        st.markdown("**Strengths**")
        for s in strengths:
            st.markdown(
                f'<div style="background:#0d2b1a; border:1px solid #1a4a2e; border-left:3px solid #22c55e;'
                f' border-radius:6px; padding:0.65rem 0.9rem; margin-bottom:0.5rem;'
                f' color:#86efac; font-size:0.85rem;">{s}</div>',
                unsafe_allow_html=True,
            )

    with col_i:
        st.markdown("**Areas to Improve**")
        for imp in improvements:
            st.markdown(
                f'<div style="background:#2b1d0a; border:1px solid #4a3010; border-left:3px solid #f59e0b;'
                f' border-radius:6px; padding:0.65rem 0.9rem; margin-bottom:0.5rem;'
                f' color:#fcd34d; font-size:0.85rem;">{imp}</div>',
                unsafe_allow_html=True,
            )

    # ── Next steps ───────────────────────────────────────────────────────────
    next_steps = summary.get("next_steps", "")
    if next_steps:
        st.info(f"**Next Steps:** {next_steps}")

    # ── Detailed Q&A review ──────────────────────────────────────────────────
    with st.expander("Full Answer Review"):
        for i, (q_obj, ev) in enumerate(zip(questions, evaluations)):
            st.markdown(f"#### Question {i+1}: {q_obj['question']}")
            st.markdown(f"**Your answer:** {ev.get('_raw_answer', '')}")
            st.markdown(f"**Score:** {ev.get('score', 0)}/10")
            st.markdown(f"**Feedback:** {ev.get('feedback', '')}")
            st.markdown(f"**Explanation:** {ev.get('explanation', '')}")
            st.divider()

    # ── Actions ──────────────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("New Interview", type="primary", use_container_width=True):
            _reset()
    with c2:
        if st.button("Home", use_container_width=True):
            _reset()

# ─────────────────────────────────────────────────────────────────────────────
# App bootstrap
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TalentScout",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
)

_inject_css()
_init_session()

page = st.session_state.page
if page == "home":
    page_home()
elif page == "interview":
    page_interview()
elif page == "results":
    page_results()
else:
    st.session_state.page = "home"
    st.rerun()

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; color:#2e2e3e; font-size:0.76rem;
                margin-top:3rem; padding-top:1.25rem; border-top:1px solid #1a1a24;">
        TalentScout &nbsp;&middot;&nbsp; Groq LLaMA &nbsp;&middot;&nbsp; Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
