
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# Locate the project root:
# backend/app/core/supabase_client.py -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")


def get_supabase_client() -> Client:
    """Create and return a Supabase client."""

    if not ENV_FILE.exists():
        raise RuntimeError(
            f".env file not found at: {ENV_FILE}"
        )

    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError(
            "Supabase credentials are missing. "
            "Check the variable names and values in your .env file."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY
    )
