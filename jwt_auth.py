"""
Auth for the FastAPI backend (api.py). Separate from auth.py, which is
Streamlit-specific (uses st.session_state, st.stop()) and doesn't apply
here - the Next.js frontend is a completely different client, so it gets
a token instead of a server-side session.

Same underlying idea as auth.py though: users live in users.yaml with
bcrypt-hashed passwords, sign-up creates that file if it doesn't exist
yet. On top of that, login issues a JWT the frontend stores and sends
back on every request; protected endpoints verify that token instead of
re-checking a password every time.
"""
import datetime

import bcrypt
import yaml
from jose import JWTError, jwt

import config

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24 * 7  # a week - re-login after that


class AuthError(Exception):
    pass


def _load_users() -> dict:
    try:
        with open(config.USERS_FILE) as f:
            data = yaml.safe_load(f) or {}
            return data.get("users", {})
    except FileNotFoundError:
        return {}


def _save_users(users: dict):
    with open(config.USERS_FILE, "w") as f:
        yaml.safe_dump({"users": users}, f)


def _require_jwt_secret():
    if not config.JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET is not set - check your .env file. Generate one with: "
            "python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )


def create_token(username: str, name: str) -> str:
    _require_jwt_secret()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {"sub": username, "name": name, "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Returns {"username": ..., "name": ...} if valid. Raises AuthError
    if the token is missing, expired, or tampered with."""
    _require_jwt_secret()
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
        return {"username": payload["sub"], "name": payload["name"]}
    except JWTError:
        raise AuthError("Invalid or expired token")


def signup(name: str, username: str, password: str) -> str:
    """Creates a new user account. Returns a JWT on success. Raises
    AuthError if the username is taken or fields are missing."""
    if not name or not username or not password:
        raise AuthError("Name, username, and password are all required")

    users = _load_users()
    if username in users:
        raise AuthError("That username is already taken")

    users[username] = {
        "name": name,
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
    }
    _save_users(users)
    return create_token(username, name)


def login(username: str, password: str) -> str:
    """Returns a JWT on success. Raises AuthError on wrong credentials."""
    users = _load_users()
    user = users.get(username)
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        raise AuthError("Wrong username or password")
    return create_token(username, user.get("name", username))
