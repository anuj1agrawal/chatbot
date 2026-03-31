"""
CLI entry point — useful for health checks and manual DB init.
The primary entry point for the browser UI is: streamlit run app.py
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def health_check() -> None:
    print("=== TalentScout AI Interviewer — Health Check ===")

    # DB
    try:
        from app.db.database import init_db
        init_db()
        print("[OK] Database initialised")
    except Exception as exc:
        print(f"[FAIL] Database: {exc}")
        sys.exit(1)

    # AI client
    try:
        from app.ai.client import get_client
        get_client()
        print("[OK] Groq AI client ready")
    except Exception as exc:
        print(f"[FAIL] AI client: {exc}")
        sys.exit(1)

    print("\nAll checks passed. Run the app with:")
    print("  streamlit run app.py")


if __name__ == "__main__":
    health_check()
