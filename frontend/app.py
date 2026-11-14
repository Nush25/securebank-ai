import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

from frontend.auth_client import (
    register,
    login,
    logout,
    resend_verification,
    ask_question,
)

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SecureBank AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "chat_history.db"
SETTINGS_PATH = DATA_DIR / "app_settings.json"

SUGGESTIONS = [
    "What is UPI and how does it work?",
    "What is the difference between NEFT and RTGS?",
    "How can I apply for a personal loan?",
    "How can I protect my bank account from fraud?",
]

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations_v2 (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_id TEXT
            )
        """)

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(conversations_v2)"
            )
        }

        if "user_id" not in columns:
            conn.execute(
                "ALTER TABLE conversations_v2 ADD COLUMN user_id TEXT"
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id)
                    REFERENCES conversations_v2(id)
                    ON DELETE CASCADE
            )
        """)


def create_conversation(user_id):
    conversation_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO conversations_v2
            (id, title, created_at, updated_at, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            conversation_id,
            "New conversation",
            now,
            now,
            user_id,
        ))

    return conversation_id


def get_conversations(user_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, title
            FROM conversations_v2
            WHERE user_id=?
            ORDER BY updated_at DESC
        """, (user_id,)).fetchall()


def conversation_belongs_to_user(conversation_id, user_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT 1
            FROM conversations_v2
            WHERE id=? AND user_id=?
        """, (str(conversation_id), user_id)).fetchone() is not None


def get_messages(conversation_id, user_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT m.role, m.content, m.sources
            FROM messages_v2 m
            JOIN conversations_v2 c
                ON c.id=m.conversation_id
            WHERE m.conversation_id=? AND c.user_id=?
            ORDER BY m.id
        """, (str(conversation_id), user_id)).fetchall()

    messages = []

    for role, content, sources in rows:
        try:
            parsed_sources = json.loads(sources) if sources else []
            if not isinstance(parsed_sources, list):
                parsed_sources = []
        except (ValueError, TypeError):
            parsed_sources = []

        messages.append({
            "role": role,
            "content": content,
            "sources": parsed_sources,
        })

    return messages


def save_message(
    conversation_id,
    user_id,
    role,
    content,
    sources=None,
):
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        owner = conn.execute("""
            SELECT 1
            FROM conversations_v2
            WHERE id=? AND user_id=?
        """, (str(conversation_id), user_id)).fetchone()

        if not owner:
            raise PermissionError(
                "Conversation does not belong to this account."
            )

        conn.execute("""
            INSERT INTO messages_v2
            (conversation_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(conversation_id),
            role,
            content,
            json.dumps(sources or [], ensure_ascii=False),
            now,
        ))

        if role == "user":
            count = conn.execute("""
                SELECT COUNT(*)
                FROM messages_v2
                WHERE conversation_id=?
            """, (str(conversation_id),)).fetchone()[0]

            if count == 1:
                clean = content.strip().replace("\n", " ")
                title = clean[:42] + (
                    "…" if len(clean) > 42 else ""
                )

                conn.execute("""
                    UPDATE conversations_v2
                    SET title=?, updated_at=?
                    WHERE id=? AND user_id=?
                """, (
                    title or "New conversation",
                    now,
                    str(conversation_id),
                    user_id,
                ))
            else:
                conn.execute("""
                    UPDATE conversations_v2
                    SET updated_at=?
                    WHERE id=? AND user_id=?
                """, (now, str(conversation_id), user_id))

        else:
            conn.execute("""
                UPDATE conversations_v2
                SET updated_at=?
                WHERE id=? AND user_id=?
            """, (now, str(conversation_id), user_id))


def delete_conversation(conversation_id, user_id):
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM conversations_v2
            WHERE id=? AND user_id=?
        """, (str(conversation_id), user_id))


initialize_database()

# ============================================================
# SETTINGS AND SESSION STATE
# ============================================================

def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as file:
            settings = json.load(file)
            if isinstance(settings, dict):
                return settings
    except (OSError, ValueError):
        pass

    return {"theme": "Light"}


def save_settings(theme):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump({"theme": theme}, file, indent=2)


DEFAULTS = {
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "user_email": None,
    "active_chat_id": None,
    "pending_question": None,
    "delete_confirmation": None,
    "theme": load_settings().get("theme", "Light"),
    "auth_notice": None,
    "registered_email": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_auth():
    for key in (
        "access_token",
        "refresh_token",
        "user_id",
        "user_email",
        "active_chat_id",
        "pending_question",
        "delete_confirmation",
    ):
        st.session_state[key] = None


def perform_logout():
    token = st.session_state.access_token

    if token:
        try:
            response = logout(token)
            if not response.ok:
                st.warning("Server logout could not be confirmed.")
        except requests.RequestException:
            st.warning("Backend unavailable. Clearing local session.")

    clear_auth()
    st.rerun()


def go_home():
    st.session_state.active_chat_id = None
    st.session_state.pending_question = None
    st.rerun()


def new_chat():
    st.session_state.active_chat_id = None
    st.session_state.pending_question = None
    st.rerun()


def queue_question(question):
    question = (question or "").strip()

    if not question:
        return

    user_id = st.session_state.user_id
    conversation_id = st.session_state.active_chat_id

    if (
        not conversation_id
        or not conversation_belongs_to_user(
            conversation_id,
            user_id,
        )
    ):
        conversation_id = create_conversation(user_id)

    st.session_state.active_chat_id = conversation_id

    save_message(
        conversation_id,
        user_id,
        "user",
        question,
    )

    st.session_state.pending_question = question
    st.rerun()


# ============================================================
# THEME
# ============================================================

DARK = st.session_state.theme == "Dark"

if DARK:
    C = {
        "bg": "#111827",
        "surface": "#1F2937",
        "alt": "#263449",
        "text": "#F3F4F6",
        "muted": "#AAB7C8",
        "border": "#37465B",
        "accent": "#5CC6D0",
        "input": "#172235",
    }
else:
    C = {
        "bg": "#F4F7FB",
        "surface": "#FFFFFF",
        "alt": "#EDF5FF",
        "text": "#173B67",
        "muted": "#71839B",
        "border": "#DCE6F2",
        "accent": "#087E8B",
        "input": "#FFFFFF",
    }


# ============================================================
# STYLING
# ============================================================

st.markdown(
    f"""
    <style>

    /* GLOBAL */
    .stApp {{
        background: {C['bg']} !important;
        color: {C['text']} !important;
    }}

    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {{
        background: {C['bg']} !important;
    }}

    [data-testid="stHeader"] {{
        background: {C['bg']} !important;
    }}

    .block-container {{
        max-width: 1100px;
        padding: 2rem 2rem 3rem;
    }}

    /* BRAND */
    .brand {{
        font-size: 25px;
        font-weight: 800;
        color: {C['text']} !important;
    }}

    .brand-caption {{
        font-size: 10px;
        letter-spacing: 1.6px;
        color: {C['muted']} !important;
        margin-top: 6px;
    }}

    .eyebrow {{
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2px;
        color: {C['accent']} !important;
        margin-bottom: 10px;
    }}

    .main-heading {{
        font-size: clamp(30px, 4vw, 42px);
        line-height: 1.2;
        font-weight: 800;
        color: {C['text']} !important;
        margin-bottom: 10px;
    }}

    .subtitle {{
        font-size: 15px;
        line-height: 1.7;
        color: {C['muted']} !important;
        margin-bottom: 28px;
    }}

    /* AUTHENTICATION AREA */
    [data-testid="stTabs"] {{
        width: 100%;
        max-width: 620px;
        margin-left: auto;
        margin-right: auto;
    }}

    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        display: flex;
        justify-content: center;
        gap: 8px;
        background: transparent !important;
        border-bottom: 1px solid {C['border']} !important;
        padding: 0 0 12px;
    }}

    [data-testid="stTabs"] button[data-baseweb="tab"] {{
        flex: 1 1 auto;
        justify-content: center;
        background: {C['surface']} !important;
        color: {C['text']} !important;
        border: 1px solid {C['border']} !important;
        border-radius: 9px !important;
        padding: 10px 12px !important;
        min-height: 42px;
        font-weight: 650 !important;
        opacity: 1 !important;
    }}

    [data-testid="stTabs"] button[data-baseweb="tab"] *,
    [data-testid="stTabs"] button[data-baseweb="tab"] p,
    [data-testid="stTabs"] button[data-baseweb="tab"] div {{
        color: {C['text']} !important;
        opacity: 1 !important;
    }}

    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
        background: {C['accent']} !important;
        border-color: {C['accent']} !important;
        color: #FFFFFF !important;
    }}

    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] * {{
        color: #FFFFFF !important;
    }}

    [data-testid="stTabs"] [data-baseweb="tab-panel"] {{
        padding: 22px 4px 10px !important;
    }}

    /* AUTHENTICATION HEADINGS */
    [data-testid="stTabs"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stTabs"] [data-testid="stMarkdownContainer"] h3 {{
        color: {C['text']} !important;
    }}

    [data-testid="stTabs"] [data-testid="stCaptionContainer"] p {{
        color: {C['muted']} !important;
    }}

    /* FORMS */
    [data-testid="stForm"] {{
        background: {C['surface']} !important;
        border: 1px solid {C['border']} !important;
        border-radius: 14px;
        padding: 18px 20px;
    }}

    [data-testid="stForm"] label,
    [data-testid="stForm"] [data-testid="stWidgetLabel"] p {{
        color: {C['text']} !important;
        font-weight: 600;
    }}

    /* INPUTS */
    .stTextInput input {{
        background: {C['input']} !important;
        color: {C['text']} !important;
        border: 1px solid {C['border']} !important;
        border-radius: 9px !important;
        min-height: 40px !important;
        height: 40px !important;
        font-size: 14px !important;
    }}

    .stTextInput input::placeholder {{
        color: {C['muted']} !important;
        opacity: 0.85;
    }}

    .stTextInput label,
    .stTextInput label p {{
        color: {C['text']} !important;
        font-size: 13px !important;
    }}

    /* BUTTONS */
    .stButton button,
    [data-testid="stFormSubmitButton"] button {{
        min-height: 40px !important;
        height: auto !important;
        border-radius: 9px !important;
        font-size: 14px !important;
        font-weight: 650 !important;
        padding: 8px 14px !important;
        white-space: normal;
        transition: all 0.2s ease;
    }}

    .stButton button {{
        background: {C['surface']} !important;
        color: {C['text']} !important;
        border: 1px solid {C['border']} !important;
    }}

    .stButton button:hover {{
        border-color: {C['accent']} !important;
        color: {C['accent']} !important;
    }}

    [data-testid="stFormSubmitButton"] button {{
        background: {C['accent']} !important;
        color: #FFFFFF !important;
        border: 1px solid {C['accent']} !important;
    }}

    [data-testid="stFormSubmitButton"] button:hover {{
        filter: brightness(0.92);
    }}

    /* GENERAL TEXT */
    h1, h2, h3, h4, h5, h6,
    p, label, li {{
        color: {C['text']};
    }}

    [data-testid="stCaptionContainer"] p {{
        color: {C['muted']} !important;
    }}

    /* WELCOME CARD */
    .welcome-card {{
        background: {C['alt']};
        border: 1px solid {C['border']};
        border-radius: 18px;
        padding: 28px;
        margin: 24px 0 30px;
    }}

    .welcome-title {{
        font-size: 24px;
        font-weight: 750;
        color: {C['text']} !important;
        margin: 8px 0 12px;
    }}

    .welcome-description {{
        font-size: 15px;
        line-height: 1.8;
        color: {C['muted']} !important;
    }}

    /* CHAT */
    [data-testid="stChatMessage"] {{
        border: 1px solid {C['border']};
        border-radius: 15px;
        padding: 12px 16px;
        margin-bottom: 12px;
        background: {C['surface']} !important;
    }}

    [data-testid="stChatMessage"] p {{
        color: {C['text']} !important;
        line-height: 1.7;
    }}

    /* EXPANDERS */
    [data-testid="stExpander"] {{
        background: {C['surface']} !important;
        border: 1px solid {C['border']} !important;
        border-radius: 11px;
    }}

    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p {{
        color: {C['text']} !important;
    }}

    /* SIDEBAR */
    section[data-testid="stSidebar"] {{
        background: {C['surface']} !important;
        border-right: 1px solid {C['border']};
    }}

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {C['text']} !important;
    }}

    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
        color: {C['muted']} !important;
    }}

    section[data-testid="stSidebar"] button {{
        border-radius: 9px;
    }}

    /* ========================================================
       SIDEBAR EXPAND / COLLAPSE CONTROL
       Explicit contrast for both LIGHT and DARK themes.
       ======================================================== */

    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"] button,
    button[data-testid="stSidebarCollapsedControl"],
    [data-testid="stHeader"] button[kind="header"] {{
        background-color: #087E8B !important;
        color: #FFFFFF !important;
        border: 1px solid #087E8B !important;
        border-radius: 0 10px 10px 0 !important;
        opacity: 1 !important;
        visibility: visible !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.22) !important;
        z-index: 99999 !important;
    }}

    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stHeader"] button[kind="header"] {{
        min-width: 38px !important;
        min-height: 38px !important;
    }}

    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] svg path,
    [data-testid="stSidebarCollapsedControl"] svg line,
    [data-testid="stSidebarCollapsedControl"] svg polyline,
    [data-testid="stHeader"] button[kind="header"] svg,
    [data-testid="stHeader"] button[kind="header"] svg path,
    [data-testid="stHeader"] button[kind="header"] svg line,
    [data-testid="stHeader"] button[kind="header"] svg polyline {{
        color: #FFFFFF !important;
        fill: none !important;
        stroke: #FFFFFF !important;
        opacity: 1 !important;
    }}

    [data-testid="stSidebarCollapsedControl"]:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover,
    [data-testid="stHeader"] button[kind="header"]:hover {{
        background-color: #066873 !important;
        border-color: #066873 !important;
        color: #FFFFFF !important;
    }}

    /* SIDEBAR BUTTON ICONS */
    section[data-testid="stSidebar"] button svg {{
        color: {C['text']} !important;
    }}

    /* RADIO */
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] p {{
        color: {C['text']} !important;
    }}

    /* ALERTS */
    [data-testid="stAlert"] {{
        border-radius: 10px;
    }}

    /* RESPONSIVE */
    @media (max-width: 640px) {{
        .block-container {{
            padding: 1rem 1rem 2rem;
        }}

        [data-testid="stTabs"] {{
            max-width: 100%;
        }}

        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            gap: 5px;
        }}

        [data-testid="stTabs"] button[data-baseweb="tab"] {{
            padding: 8px 6px !important;
            font-size: 12px !important;
        }}

        [data-testid="stForm"] {{
            padding: 14px;
        }}
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOGIN / REGISTRATION / EMAIL VERIFICATION
# ============================================================

if not st.session_state.access_token:

    st.markdown(
        """
        <div style="text-align:center; padding:24px 0 18px;">
            <div style="font-size:42px;">🏦</div>
            <div class="brand">SecureBank AI</div>
            <div class="brand-caption">
                BANKING KNOWLEDGE ASSISTANT
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.auth_notice:
        st.info(st.session_state.auth_notice)

    tab_login, tab_signup, tab_verify = st.tabs([
        "Login",
        "Create account",
        "Verify email",
    ])

    # LOGIN
    with tab_login:
        st.subheader("Welcome back")
        st.caption(
            "Sign in using your verified email address and password."
        )

        with st.form("login_form"):
            email = st.text_input(
                "Email address",
                placeholder="name@example.com",
                key="login_email",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password",
            )

            login_submit = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

        if login_submit:
            if not email.strip() or not password:
                st.warning(
                    "Please enter both email address and password."
                )
            else:
                try:
                    response = login(email.strip(), password)

                    if response.ok:
                        data = response.json()
                        auth_data = data.get("data", data)
                        user = auth_data.get("user") or {}

                        access_token = auth_data.get("access_token")
                        refresh_token = auth_data.get("refresh_token")
                        user_id = user.get("id")
                        user_email = user.get("email") or email.strip()

                        if not access_token or not user_id:
                            st.error(
                                "Login response is missing required "
                                "session information. Please check "
                                "the FastAPI login response."
                            )
                        else:
                            st.session_state.access_token = access_token
                            st.session_state.refresh_token = refresh_token
                            st.session_state.user_id = str(user_id)
                            st.session_state.user_email = user_email
                            st.session_state.active_chat_id = None
                            st.session_state.pending_question = None
                            st.session_state.auth_notice = None
                            st.rerun()

                    else:
                        try:
                            detail = response.json().get(
                                "detail",
                                "Login failed.",
                            )
                        except ValueError:
                            detail = "Login failed."

                        st.error(str(detail))

                except requests.RequestException:
                    st.error(
                        "Cannot connect to FastAPI. "
                        "Check that the backend is running."
                    )

                except (ValueError, TypeError, AttributeError):
                    st.error(
                        "The backend returned an unexpected login response."
                    )

    # SIGNUP
    with tab_signup:
        st.subheader("Create your account")
        st.caption(
            "Enter your details. We will send a verification link "
            "to your email."
        )

        with st.form("signup_form"):
            signup_email = st.text_input(
                "Email address",
                placeholder="name@example.com",
                key="signup_email",
            )

            confirm_email = st.text_input(
                "Confirm email address",
                placeholder="Re-enter your email",
                key="confirm_signup_email",
            )

            signup_password = st.text_input(
                "Password",
                type="password",
                placeholder="At least 8 characters",
                key="signup_password",
            )

            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                placeholder="Re-enter your password",
                key="confirm_signup_password",
            )

            signup_submit = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

        if signup_submit:
            email_one = signup_email.strip().lower()
            email_two = confirm_email.strip().lower()

            if not email_one or not email_two:
                st.warning("Enter and confirm your email address.")

            elif email_one != email_two:
                st.error("The email addresses do not match.")

            elif len(signup_password) < 8:
                st.warning(
                    "Password must contain at least 8 characters."
                )

            elif signup_password != confirm_password:
                st.error("The passwords do not match.")

            else:
                try:
                    response = register(
                        email_one,
                        signup_password,
                    )

                    if response.ok:
                        st.session_state.registered_email = email_one
                        st.session_state.auth_notice = (
                            "Account created. Check your inbox and click "
                            "the Supabase verification link before logging in."
                        )

                        st.success(
                            "Your account registration was submitted."
                        )

                        st.info(
                            "1. Open your email inbox.\n\n"
                            "2. Find the SecureBank AI confirmation email.\n\n"
                            "3. Click the verification link.\n\n"
                            "4. Return to the Login tab."
                        )
                    else:
                        try:
                            detail = response.json().get(
                                "detail",
                                "Registration failed.",
                            )
                        except ValueError:
                            detail = "Registration failed."

                        st.error(str(detail))

                except requests.RequestException:
                    st.error(
                        "Cannot connect to FastAPI. "
                        "Check that the backend is running."
                    )

    # VERIFY EMAIL
    with tab_verify:
        st.subheader("Email verification")

        st.write(
            "Already registered but did not receive the email? "
            "Request another confirmation link."
        )

        verify_email = st.text_input(
            "Email address",
            value=st.session_state.registered_email,
            placeholder="name@example.com",
            key="resend_email",
        )

        if st.button(
            "Resend verification email",
            use_container_width=True,
            key="resend_button",
        ):
            if not verify_email.strip():
                st.warning(
                    "Enter the email address you registered with."
                )
            else:
                try:
                    response = resend_verification(
                        verify_email.strip()
                    )

                    if response.ok:
                        st.success(
                            "Verification email request submitted. "
                            "Check your inbox and Spam/Junk folder."
                        )
                    else:
                        try:
                            data = response.json()
                            detail = (
                                data.get("msg")
                                or data.get("message")
                                or data.get("error_description")
                                or "Could not resend the verification email."
                            )
                        except ValueError:
                            detail = (
                                "Could not resend the verification email."
                            )

                        st.error(str(detail))

                except (
                    requests.RequestException,
                    RuntimeError,
                ) as error:
                    st.error(str(error))

        st.caption(
            "After clicking the link in your email, "
            "return to Login and sign in."
        )

    st.stop()


# ============================================================
# AUTHENTICATED SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding:10px 0 16px;">
            <div class="brand">🏦 SecureBank AI</div>
            <div class="brand-caption">
                BANKING KNOWLEDGE ASSISTANT
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("SIGNED IN AS")
    st.markdown(
        f"**{st.session_state.user_email or 'User'}**"
    )

    if st.button(
        "⌂  Home",
        use_container_width=True,
        key="sidebar_home",
    ):
        go_home()

    if st.button(
        "＋  New conversation",
        use_container_width=True,
        key="sidebar_new_chat",
    ):
        new_chat()

    st.divider()
    st.markdown("### Appearance")

    selected_theme = st.radio(
        "Theme",
        ["Light", "Dark"],
        index=0 if st.session_state.theme == "Light" else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="theme_radio",
    )

    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        save_settings(selected_theme)
        st.rerun()

    st.divider()
    st.markdown("### Conversation history")

    conversations = get_conversations(
        st.session_state.user_id
    )

    if not conversations:
        st.caption("Your conversations will appear here.")

    for conversation_id, title in conversations[:30]:
        conversation_id = str(conversation_id)
        label = str(title or "Conversation")

        if len(label) > 26:
            label = label[:26] + "…"

        open_col, delete_col = st.columns([5, 1])

        with open_col:
            if st.button(
                "💬 " + label,
                key=f"open_{conversation_id}",
                use_container_width=True,
            ):
                st.session_state.active_chat_id = conversation_id
                st.session_state.pending_question = None
                st.rerun()

        with delete_col:
            if st.button(
                "🗑",
                key=f"delete_{conversation_id}",
                help="Delete conversation",
            ):
                st.session_state.delete_confirmation = conversation_id
                st.rerun()

        if st.session_state.delete_confirmation == conversation_id:
            st.warning("Delete this conversation?")

            yes_col, no_col = st.columns(2)

            with yes_col:
                if st.button(
                    "Delete",
                    key=f"confirm_{conversation_id}",
                ):
                    delete_conversation(
                        conversation_id,
                        st.session_state.user_id,
                    )

                    if (
                        st.session_state.active_chat_id
                        == conversation_id
                    ):
                        st.session_state.active_chat_id = None

                    st.session_state.delete_confirmation = None
                    st.rerun()

            with no_col:
                if st.button(
                    "Cancel",
                    key=f"cancel_{conversation_id}",
                ):
                    st.session_state.delete_confirmation = None
                    st.rerun()

    st.divider()
    st.markdown("### About")

    st.caption(
        "A locally powered banking knowledge assistant "
        "that answers using your supplied documents."
    )

    st.caption(
        "Ollama • Qwen3 • FAISS • FastAPI • Supabase Auth"
    )

    st.divider()

    if st.button(
        "↪  Logout",
        use_container_width=True,
        key="sidebar_logout",
    ):
        perform_logout()


# ============================================================
# MAIN PAGE HEADER
# ============================================================

header_left, header_right = st.columns([5, 1])

with header_right:
    if st.button(
        "Logout",
        key="main_logout",
        use_container_width=True,
    ):
        perform_logout()

st.markdown(
    '<div class="eyebrow">BANKING KNOWLEDGE ASSISTANT</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-heading">How can we help you?</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Get clear answers to your banking questions, '
    'with supporting information from banking documents.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# HOME SCREEN
# ============================================================

if st.session_state.active_chat_id is None:

    st.html("""
    <div class="welcome-card">
        <div class="eyebrow">WELCOME TO SECUREBANK AI</div>
        <div class="welcome-title">
            Banking questions, made simpler.
        </div>
        <div class="welcome-description">
            Ask about accounts, digital payments, loans, credit cards,
            transactions and banking security. Write naturally and
            get clear explanations.
        </div>
    </div>
    """)

    st.markdown(
        '<div style="font-size:19px;font-weight:750;margin:22px 0 14px">'
        'Explore suggested questions'
        '</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    for index, suggestion in enumerate(SUGGESTIONS):
        with (left if index % 2 == 0 else right):
            if st.button(
                suggestion,
                key=f"suggestion_{index}",
                use_container_width=True,
            ):
                queue_question(suggestion)


# ============================================================
# EXISTING CONVERSATION
# ============================================================

active_id = st.session_state.active_chat_id

if active_id:
    user_id = st.session_state.user_id

    if not conversation_belongs_to_user(active_id, user_id):
        st.session_state.active_chat_id = None
        st.rerun()

    messages = get_messages(active_id, user_id)

    for message in messages:

        if message["role"] == "user":
            _, user_col = st.columns([1, 3])

            with user_col:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])

        else:
            assistant_col, _ = st.columns([3, 1])

            with assistant_col:
                with st.chat_message("assistant", avatar="🏦"):
                    st.markdown(message["content"])

                    if message.get("sources"):
                        with st.expander("📚 Supporting documents"):
                            for source in message["sources"]:
                                st.markdown(
                                    f"**{source.get('filename', 'Banking document')}**"
                                )

                                if source.get("excerpt"):
                                    st.caption(source["excerpt"])

                                if source.get("similarity") is not None:
                                    st.caption(
                                        "Retrieval similarity: "
                                        f"{source['similarity']}"
                                    )


# ============================================================
# PROCESS QUEUED QUESTION
# ============================================================

if st.session_state.pending_question:

    question = st.session_state.pending_question
    conversation_id = st.session_state.active_chat_id

    st.session_state.pending_question = None

    answer = ""
    sources = []

    with st.chat_message("assistant", avatar="🏦"):
        with st.spinner(
            "Searching your banking documents and preparing an answer..."
        ):
            try:
                result = ask_question(
                    question,
                    st.session_state.access_token,
                )

                answer = result.get(
                    "answer",
                    "I couldn't generate an answer. Please try again.",
                )

                sources = result.get("sources", [])

                if not isinstance(sources, list):
                    sources = []

            except requests.exceptions.HTTPError as error:
                if (
                    error.response is not None
                    and error.response.status_code == 401
                ):
                    clear_auth()
                    st.session_state.auth_notice = (
                        "Your session expired. Please log in again."
                    )
                    st.rerun()

                answer = (
                    "The backend could not process your request. "
                    "Please try again."
                )

            except requests.exceptions.ConnectionError:
                answer = (
                    "I couldn't connect to FastAPI. "
                    "Make sure the backend is running."
                )

            except requests.exceptions.Timeout:
                answer = (
                    "The request took too long. "
                    "Check that Ollama and FastAPI are running."
                )

            except requests.RequestException:
                answer = (
                    "The backend request failed. Please try again."
                )

            except (ValueError, TypeError):
                answer = (
                    "The backend returned an invalid response."
                )

    if conversation_belongs_to_user(
        conversation_id,
        st.session_state.user_id,
    ):
        save_message(
            conversation_id,
            st.session_state.user_id,
            "assistant",
            answer,
            sources,
        )

    st.rerun()


# ============================================================
# QUESTION INPUT
# ============================================================

with st.form(
    "question_form",
    clear_on_submit=True,
):
    input_col, send_col = st.columns([8, 1])

    with input_col:
        question_input = st.text_input(
            "Your question",
            placeholder="Ask anything about banking...",
            label_visibility="collapsed",
        )

    with send_col:
        submitted = st.form_submit_button(
            "Send ➤",
            use_container_width=True,
        )

if submitted and question_input.strip():
    queue_question(question_input)


# ============================================================
# AUTO SCROLL
# ============================================================

components.html(
    """
    <script>
    (() => {
        const doc = window.parent.document;

        const scroll = () => {
            const selectors = [
                '[data-testid="stMain"]',
                '[data-testid="stAppViewContainer"]',
                'section.main'
            ];

            for (const selector of selectors) {
                const element = doc.querySelector(selector);

                if (element) {
                    element.scrollTo({
                        top: element.scrollHeight,
                        behavior: "smooth"
                    });
                }
            }

            window.parent.scrollTo({
                top: doc.body.scrollHeight,
                behavior: "smooth"
            });
        };

        requestAnimationFrame(scroll);
        setTimeout(scroll, 150);
        setTimeout(scroll, 450);
    })();
    </script>
    """,
    height=1,
)