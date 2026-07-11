"""
Login screen with a self-serve sign-up tab, so nobody has to run a
Python command to create their own account. Users live in users.yaml
with bcrypt-hashed passwords - no external auth library, just a form and
a hash check. This keeps each user's session (and therefore their
history) tied to a username, so one person never sees another person's
prescriptions.
"""
import bcrypt
import streamlit as st
import yaml

import config


def _load_users() -> dict:
    try:
        with open(config.USERS_FILE) as f:
            data = yaml.safe_load(f) or {}
            return data.get("users", {})
    except FileNotFoundError:
        return {}  # no file yet - fine, sign-up will create it


def _save_users(users: dict):
    with open(config.USERS_FILE, "w") as f:
        yaml.safe_dump({"users": users}, f)


def _login_form():
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Log in", type="primary"):
        users = _load_users()
        user = users.get(username)
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            st.session_state["username"] = username
            st.session_state["name"] = user.get("name", username)
            st.rerun()
        else:
            st.error("Wrong username or password.")


def _signup_form():
    name = st.text_input("Your name", key="signup_name")
    username = st.text_input("Choose a username", key="signup_username")
    password = st.text_input("Choose a password", type="password", key="signup_password")

    if st.button("Create account", type="primary"):
        if not name or not username or not password:
            st.error("Fill in all three fields.")
            return

        users = _load_users()
        if username in users:
            st.error("That username is already taken - pick another.")
            return

        users[username] = {
            "name": name,
            "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        }
        _save_users(users)

        st.session_state["username"] = username
        st.session_state["name"] = name
        st.rerun()


def require_login() -> tuple[str, str]:
    """Shows a login/sign-up form and stops the app until someone logs
    in. Returns (username, display_name) once they do."""
    if "username" in st.session_state:
        return st.session_state["username"], st.session_state["name"]

    st.title("💊 PresciMate")

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])
    with tab_login:
        _login_form()
    with tab_signup:
        _signup_form()

    st.stop()  # nothing below this renders until login succeeds


def logout():
    for key in ("username", "name"):
        st.session_state.pop(key, None)
    st.rerun()
