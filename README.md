# TalentScout AI Interviewer

> A production-ready, Render-deployable AI interview web dashboard built with Streamlit and Groq LLaMA.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard (app.py)                  │
│   ┌──────────┐   ┌────────────────────┐   ┌───────────────────┐ │
│   │  Home    │   │  Interview Chat    │   │  Results          │ │
│   │  Page    │   │  (Maya AI)         │   │  Dashboard        │ │
│   └──────────┘   └────────────────────┘   └───────────────────┘ │
└─────────────────────────────┬────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐
   │  app/ai/    │   │  app/services/   │   │  app/db/         │
   │  client     │   │  user_service    │   │  database.py     │
   │  q_gen      │   │  iv_service      │   │  SQLite  (dev)   │
   │  evaluator  │   └──────────────────┘   │  PostgreSQL(prod)│
   │  feedback   │       app/models/        └──────────────────┘
   └─────────────┘   user · interview · question · answer · result
```

## POC Flow

```
User enters skills
       │
       ▼
AI generates 5 tailored questions
       │
       ▼
Candidate answers each question
       │
       ▼
AI scores each answer (0-10)
       │
       ▼
Summary generated (grade, strengths, recommendation)
       │
       ▼
Results dashboard displayed
```

## Folder Structure

```
ai-interviewer/
├── app.py                         # Streamlit dashboard entry point
├── main.py                        # CLI / health-check entry point
├── requirements.txt
├── Procfile                       # Render process definition
├── render.yaml                    # Render deployment manifest
├── .streamlit/
│   └── config.toml                # Streamlit server + theme config
└── app/
    ├── ai/
    │   ├── client.py              # Groq client singleton
    │   ├── question_generator.py  # Skill-based question generation
    │   ├── answer_evaluator.py    # Answer scoring (0-10) + feedback
    │   └── feedback_generator.py  # Interview summary + recommendation
    ├── models/
    │   ├── user.py                # User table
    │   ├── interview.py           # Interview table
    │   ├── question.py            # Question table
    │   ├── answer.py              # Answer table (score, feedback)
    │   └── result.py              # Result table (grade, summary)
    ├── services/
    │   ├── user_service.py        # User CRUD
    │   └── interview_service.py   # Interview lifecycle management
    └── utils/
        ├── logger.py              # Structured logger
        ├── errors.py              # Custom exception classes
        └── validators.py          # Input validation helpers
```

---

## Quick Start (Local)

### 1. Clone and install

```bash
git clone <repo-url>
cd ai-interviewer
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY
```

Get a free Groq API key at https://console.groq.com

### 3. Run

```bash
streamlit run app.py
```

Opens at http://localhost:8501.

---

## Environment Variables

| Variable       | Required | Description                                         |
|----------------|----------|-----------------------------------------------------|
| GROQ_API_KEY   | Yes      | Groq API key (free at console.groq.com)             |
| DATABASE_URL   | Optional | PostgreSQL URL. Omit for SQLite (local dev)         |
| ENVIRONMENT    | Optional | development or production (default: production)     |
| PORT           | Render   | Set automatically by Render                         |

---

## Database

| Mode       | Driver          | When                        |
|------------|-----------------|-----------------------------|
| Local dev  | SQLite          | DATABASE_URL is empty       |
| Production | PostgreSQL      | DATABASE_URL is set         |

Tables: users, interviews, questions, answers, results

Tables are created automatically on first run via init_db().

---

## Scoring System

| Grade | Range   | Label         |
|-------|---------|---------------|
| A     | 90-100% | Excellent     |
| B     | 75-89%  | Good          |
| C     | 60-74%  | Average       |
| D     | 40-59%  | Below Average |
| F     | 0-39%   | Needs Work    |

Each question is scored **0-10** by the AI evaluator.
Final score = sum / (questions * 10) * 100.

---

## Deploy to Render

### Option A — render.yaml (recommended)

1. Push your code to GitHub/GitLab.
2. Connect the repo to Render.
3. Render auto-detects render.yaml and creates:
   - Web service (talentscout-ai-interviewer)
   - PostgreSQL database (talentscout-db)
4. Add secret env var: GROQ_API_KEY
5. Click Deploy.

### Option B — Manual Render setup

1. Create a Web Service on Render.
2. Connect your repo.
3. Set:
   - Build Command:  pip install -r requirements.txt
   - Start Command:  streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
4. Add environment variables:
   - GROQ_API_KEY  = your key
   - DATABASE_URL  = connection string from Render PostgreSQL
   - ENVIRONMENT   = production
5. Create a PostgreSQL database and link it.

### Connecting Render PostgreSQL

In your Render dashboard:
1. Go to your database > Info tab.
2. Copy the Internal Database URL.
3. Add it as DATABASE_URL env var in your web service.

render.yaml handles this automatically via fromDatabase.connectionString.

---

## Tech Stack

- Frontend / UI:  Streamlit
- AI / LLM:       Groq Cloud (llama-3.1-8b-instant)
- ORM:            SQLAlchemy 2.x
- Database:       SQLite (dev) / PostgreSQL (prod)
- Deployment:     Render
