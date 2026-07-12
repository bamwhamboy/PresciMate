"""
Visual theme for PresciMate. Streamlit's native theme (.streamlit/config.toml)
handles the base colors; this adds what config.toml can't do alone - the
gradient background, glass-style card surfaces, and a soft pill-shaped
glow behind the sidebar title, tying back to the 💊 branding without
being literal about it.

Streamlit's internal DOM (the data-testid attributes below) can shift
between versions - if a future Streamlit upgrade changes these, the
custom styling may need updating, though the app will still work fine
without it (it just falls back to plain Streamlit dark theme).
"""
import streamlit as st

_CSS = """
<style>
/* Gradient background instead of flat black - deep indigo to plum,
   keeps the dark-mode feel but adds depth instead of a flat color */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #1A1625 0%, #241B33 45%, #2E1D2C 100%);
    background-attachment: fixed;
}

[data-testid="stHeader"] {
    background: transparent;
}

/* Sidebar: slightly lighter glass panel over the same gradient family */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(36, 30, 51, 0.92) 0%, rgba(30, 24, 43, 0.92) 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}

/* Signature element: a soft pill-shaped glow behind the sidebar title -
   quiet, not literal, just enough to feel intentional rather than default */
[data-testid="stSidebar"] > div:first-child::before {
    content: "";
    position: absolute;
    top: -60px;
    left: 50%;
    transform: translateX(-50%) rotate(-18deg);
    width: 340px;
    height: 140px;
    border-radius: 999px;
    background: radial-gradient(ellipse at center, rgba(255, 107, 84, 0.22) 0%, rgba(255, 107, 84, 0) 70%);
    pointer-events: none;
    z-index: 0;
}

/* Glass-card surfaces for info/warning boxes and expanders, instead of
   Streamlit's flat default fill */
[data-testid="stExpander"],
div[data-testid="stAlert"] {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    backdrop-filter: blur(6px);
}

/* Buttons: soften the corners, add a subtle lift on hover */
.stButton > button {
    border-radius: 10px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(255, 107, 84, 0.25);
}

/* Uploaded image and chat bubbles: match the glass-card language */
[data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 14px;
}
</style>
"""


def apply():
    st.markdown(_CSS, unsafe_allow_html=True)
