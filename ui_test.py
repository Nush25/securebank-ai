
import streamlit as st

st.set_page_config(
    page_title="UI Test",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Streamlit UI Test")

tab1, tab2, tab3 = st.tabs([
    "Login",
    "Create account",
    "Verify email"
])

with tab1:
    st.header("Welcome back")
    st.text_input("Email")
    st.text_input("Password", type="password")

with tab2:
    st.header("Create account")
    st.text_input("New email")
    st.text_input("New password", type="password")

with tab3:
    st.header("Verify email")
    st.text_input("Verification email")

with st.sidebar:
    st.title("Sidebar Test")
    st.write("If you can see this, the sidebar works.")
