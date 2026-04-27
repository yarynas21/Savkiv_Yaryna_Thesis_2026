"""
Single place for all inline CSS the Streamlit app injects via ``st.markdown``.

Kept pure-string and import-light so ``app.py`` can include it at the very top
without pulling in Streamlit-specific dependencies prematurely.
"""

from __future__ import annotations

import streamlit as st


APP_CSS: str = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stAppViewContainer"] { background: #F5F7FA; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="block-container"] { padding-top: 1.5rem; }

/* ── Auth page full-screen background ─────────────────────────────── */
.auth-page-bg {
    position: fixed; inset: 0;
    background: linear-gradient(135deg, #0f2744 0%, #1a3a5c 40%, #1F6FEB 100%);
    z-index: -1;
}
.auth-page-bg::after {
    content: '';
    position: absolute; inset: 0;
    background-image:
        radial-gradient(circle at 20% 80%, rgba(31,111,235,0.3) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(123,47,190,0.2) 0%, transparent 50%);
}

/* ── Auth card ─────────────────────────────────────────────────────── */
.auth-card {
    background: rgba(255,255,255,0.97);
    border-radius: 24px;
    padding: 44px 48px 40px;
    box-shadow: 0 24px 80px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.1);
    backdrop-filter: blur(20px);
}
.auth-logo { text-align: center; margin-bottom: 28px; }
.auth-logo-icon { font-size: 3.2rem; display: block; margin-bottom: 10px; line-height: 1; }
.auth-title {
    font-size: 1.75rem; font-weight: 800; color: #0f2744;
    letter-spacing: -0.03em; margin-bottom: 4px;
}
.auth-sub { color: #8896A8; font-size: 0.875rem; }

/* ── Input fields ──────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #E2E8F0 !important;
    padding: 10px 14px !important;
    font-size: 0.9rem !important;
    background: #FAFBFC !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #1F6FEB !important;
    box-shadow: 0 0 0 3px rgba(31,111,235,0.12) !important;
    background: white !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 4px;
    background: #F1F5F9;
    border-radius: 10px;
    padding: 4px;
    border-bottom: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: #64748B !important;
    padding: 8px 16px !important;
    border: none !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: white !important;
    color: #1F6FEB !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}

/* ── Primary button ────────────────────────────────────────────────── */
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #1F6FEB, #1558c0) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    padding: 10px !important;
    transition: opacity 0.2s, transform 0.1s !important;
}
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover,
[data-testid="stButton"] button[kind="primary"]:hover {
    opacity: 0.92 !important;
    transform: translateY(-1px) !important;
}

.mas-header {
    background: linear-gradient(135deg, #1a3a5c 0%, #1F6FEB 100%);
    color: white;
    padding: 20px 28px;
    border-radius: 16px;
    margin-bottom: 0;
    box-shadow: 0 4px 20px rgba(31,111,235,0.25);
    display: flex;
    align-items: center;
    gap: 16px;
}
.mas-header-icon { font-size: 2.2rem; line-height: 1; }
.mas-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
.mas-header p  { margin: 3px 0 0; opacity: 0.75; font-size: 0.82rem; }

.user-card {
    background: white;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    text-align: center;
    border: 1px solid #E8EDF5;
}
.user-avatar {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #1F6FEB, #7B2FBE);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; font-weight: 700; color: white;
    margin: 0 auto 8px;
}
.user-name { font-weight: 600; font-size: 0.88rem; color: #1a1a2e; }
.user-role { font-size: 0.75rem; color: #8896A8; margin-top: 2px; }

.agent-card {
    background: white;
    border: 1px solid #E8EDF5;
    border-radius: 10px;
    padding: 10px 14px;
    margin: 5px 0;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: box-shadow 0.2s;
}
.agent-card-active {
    border-color: #34C759;
    background: #F0FFF4;
    box-shadow: 0 0 0 2px rgba(52,199,89,0.15);
}
.agent-card-done   { border-color: #1F6FEB; background: #EFF6FF; }
.agent-card-waiting{ border-color: #FF9500; background: #FFFBF0; }
.agent-card-pending{ background: #FFFFFF; border-color: #D6DEE8; opacity: 1; }

.agent-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-active  { background: #34C759; box-shadow: 0 0 6px rgba(52,199,89,0.6); }
.dot-done    { background: #1F6FEB; }
.dot-waiting { background: #FF9500; }
.dot-pending { background: #94A3B8; }

.agent-label { font-size: 0.82rem; font-weight: 500; color: #374151; flex: 1; }
.agent-status-text { font-size: 0.72rem; font-weight: 600; }
.status-active  { color: #15803D; }
.status-done    { color: #1D4ED8; }
.status-waiting { color: #B45309; }
.status-pending { color: #64748B; }

.progress-wrap {
    background: white;
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid #E8EDF5;
    margin-bottom: 6px;
}
.progress-label {
    font-size: 0.78rem; font-weight: 600; color: #6B7280;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
}
.progress-bar-bg { background: #E8EDF5; border-radius: 99px; height: 6px; overflow: hidden; }
.progress-bar-fill {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, #1F6FEB, #34C759);
    transition: width 0.4s ease;
}
.progress-pct { font-size: 0.75rem; color: #1F6FEB; font-weight: 700; text-align: right; margin-top: 4px; }

.section-title {
    font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: #94A3B8; margin: 16px 0 8px;
}

.component-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.component-card { background: #FFFFFF; border: 1px solid #E8EDF5; border-radius: 10px; padding: 10px 12px; }
.component-title { font-size: 0.9rem; font-weight: 600; color: #1F2937; margin-bottom: 4px; }
.component-meta  { font-size: 0.78rem; color: #64748B; line-height: 1.4; }

.cost-card {
    background: linear-gradient(135deg, #F0FFF4, #EFF6FF);
    border: 1px solid #BBF7D0; border-radius: 12px;
    padding: 12px 16px; margin: 4px 0;
}

.auth-logo { text-align: center; margin-bottom: 24px; }
.auth-logo-icon { font-size: 3rem; display: block; margin-bottom: 8px; }
.auth-title { font-size: 1.6rem; font-weight: 800; color: #1a3a5c; letter-spacing: -0.03em; }
.auth-sub { color: #8896A8; font-size: 0.88rem; margin-top: 4px; }

[data-testid="stVerticalBlockBorderWrapper"] div::-webkit-scrollbar { width: 4px; }
[data-testid="stVerticalBlockBorderWrapper"] div::-webkit-scrollbar-thumb { background: #E8EDF5; border-radius: 99px; }

[data-testid="stChatMessage"] {
    background: white; border-radius: 12px; border: 1px solid #F0F4F8; margin-bottom: 4px;
}

.done-banner {
    background: linear-gradient(135deg, #F0FFF4, #EFF6FF);
    border: 1.5px solid #34C759;
    border-radius: 14px; padding: 18px 20px; text-align: center;
}
.done-banner h3 { color: #15803D; margin: 0 0 6px; font-size: 1.1rem; }
.done-banner p  { color: #374151; margin: 0; font-size: 0.85rem; }

[data-testid="stTextArea"] textarea {
    border-radius: 10px !important;
    border-color: #E8EDF5 !important;
    font-size: 0.9rem !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: #1F6FEB !important;
    box-shadow: 0 0 0 2px rgba(31,111,235,0.15) !important;
}
</style>
"""


def inject() -> None:
    """Attach the stylesheet (call once, right after ``st.set_page_config``)."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
