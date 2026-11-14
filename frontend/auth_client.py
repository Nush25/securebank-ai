import os
from pathlib import Path
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
TIMEOUT = 30


def register(email: str, password: str):
    return requests.post(
        f"{BACKEND_URL}/auth/register",
        json={"email": email.strip().lower(), "password": password},
        timeout=TIMEOUT,
    )


def login(email: str, password: str):
    return requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": email.strip().lower(), "password": password},
        timeout=TIMEOUT,
    )


def logout(access_token: str):
    return requests.post(
        f"{BACKEND_URL}/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT,
    )


def resend_verification(email: str):
    """Request a new Supabase signup confirmation email."""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("Supabase URL or publishable key is missing from .env.")
    return requests.post(
        f"{SUPABASE_URL}/auth/v1/resend",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
        },
        json={"type": "signup", "email": email.strip().lower()},
        timeout=TIMEOUT,
    )


def ask_question(question: str, access_token: str):
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={"question": question},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=180,
    )
    response.raise_for_status()
    return response.json()
