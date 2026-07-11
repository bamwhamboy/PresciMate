"""
Simple login screen. Users live in users.yaml with bcrypt-hashed
passwords - no external auth library, just a form and a hash check.
This keeps each user's session (and therefore their history) tied to a
username, so one person never sees another person's prescriptions.
"""
import bcrypt
import streamlit as st
import yaml

import config


def _load_users() -> dict:
    try:
        with open(config.USERS_FILE) as f:
            return yaml.safe_load(f).get("users", {})
    except FileNotFoundError:
        st.error(
            f"No users file found at '{config.USERS_FILE}'. Copy "
            "users.example.yaml to users.yaml and add at least one user "
            "(see the README for how to generate a password hash)."
        )
        st.stop()


def require_login() -> tuple[str, str]:
    """Shows a login form and stops the app until someone logs in.
    Returns (username, display_name) once they do."""
    if "username" in st.session_state:
        return st.session_state["username"], st.session_state["name"]

    st.title("💊 PresciMate")
    st.subheader("Log in")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log in", type="primary"):
        users = _load_users()
        user = users.get(username)
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            st.session_state["username"] = username
            st.session_state["name"] = user.get("name", username)
            st.rerun()
        else:
            st.error("Wrong username or password.")

    st.stop()  # nothing below this renders until login succeeds


def logout():
    for key in ("username", "name"):
        st.session_state.pop(key, None)
    st.rerun()
