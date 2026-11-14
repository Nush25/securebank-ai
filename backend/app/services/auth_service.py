
import requests

from backend.app.core.supabase_client import (
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY,
    get_supabase_client,
)


def register_user(email: str, password: str):
    supabase = get_supabase_client()

    try:
        response = supabase.auth.sign_up({
            "email": email.strip().lower(),
            "password": password,
        })

        user = response.user
        session = response.session

        if not user:
            raise ValueError("Registration could not be completed.")

        return {
            "success": True,
            "message": (
                "Registration successful. Please check your email "
                "and verify your account before logging in."
                if session is None
                else "Registration successful."
            ),
            "user": {
                "id": str(user.id),
                "email": user.email,
            },
            "session": session,
        }

    except Exception as error:
        raise ValueError(f"Registration failed: {error}") from error


def login_user(email: str, password: str):
    supabase = get_supabase_client()

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email.strip().lower(),
            "password": password,
        })

        user = response.user
        session = response.session

        if not user or not session:
            raise ValueError("Login failed. Please verify your email.")

        return {
            "success": True,
            "message": "Login successful.",
            "user": {
                "id": str(user.id),
                "email": user.email,
            },
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }

    except Exception as error:
        raise ValueError(f"Login failed: {error}") from error


def logout_user(access_token: str):
    """
    Revoke the authenticated Supabase session.
    """
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise ValueError("Supabase configuration is missing.")

    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/logout",
            headers={
                "apikey": SUPABASE_PUBLISHABLE_KEY,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=15,
        )

        if response.status_code not in (200, 204):
            raise ValueError("Supabase could not revoke this session.")

        return {
            "success": True,
            "message": "Logged out successfully.",
        }

    except requests.RequestException as error:
        raise ValueError("Unable to contact Supabase for logout.") from error
