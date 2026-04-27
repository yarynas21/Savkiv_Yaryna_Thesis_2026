"""
Single place for HTTP traffic between the Streamlit app and the FastAPI
backend. All ``views/*`` modules use only this module — never touch ``httpx``
directly.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_BASE: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def logout() -> None:
    """Flush all Streamlit session state and re-run."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def login(username: str, password: str) -> bool:
    try:
        resp = httpx.post(
            f"{API_BASE}/auth/token",
            json={"username": username, "password": password},
            timeout=15.0,
        )
    except Exception:
        return False
    if resp.status_code != 200:
        return False
    data = resp.json()
    st.session_state["access_token"] = data["access_token"]
    try:
        me = httpx.get(f"{API_BASE}/auth/me", headers=auth_headers(), timeout=10.0)
    except Exception:
        return False
    if me.status_code != 200:
        return False
    st.session_state["current_user"] = me.json()
    return True


def register(email: str, username: str, password: str) -> tuple[bool, str]:
    try:
        resp = httpx.post(
            f"{API_BASE}/auth/register",
            json={"email": email, "username": username, "password": password},
            timeout=15.0,
        )
    except Exception as exc:
        return False, str(exc)
    if resp.status_code == 201:
        return True, ""
    try:
        return False, resp.json().get("detail", "Помилка реєстрації")
    except Exception:
        return False, resp.text


def api(method: str, path: str, *, json: Any | None = None,
        timeout: float = 120.0, raise_on_error: bool = False) -> Any:
    """Generic request wrapper — returns parsed JSON or None on failure.

    Surfaces 401 as a forced logout, which triggers the auth gate again.
    """
    url = f"{API_BASE}{path}"
    try:
        resp = httpx.request(
            method, url, timeout=timeout, headers=auth_headers(), json=json
        )
    except httpx.ConnectError:
        st.error(
            f"Не вдалося підключитися до бекенду ({API_BASE}). "
            "Переконайтеся, що FastAPI-сервер запущено."
        )
        return None
    except Exception as exc:
        st.error(f"Несподівана помилка: {exc}")
        return None

    if resp.status_code == 401:
        st.warning("Сесія закінчилася. Будь ласка, увійдіть знову.")
        logout()
        return None

    if resp.status_code >= 400:
        detail = resp.text
        try:
            detail = resp.json().get("detail", detail)
        except Exception:
            pass
        if raise_on_error:
            raise RuntimeError(f"[{resp.status_code}] {detail}")
        st.error(f"Помилка API [{resp.status_code}]: {detail}")
        return None

    if resp.status_code == 204 or not resp.content:
        return {}
    try:
        return resp.json()
    except Exception:
        return resp.content


def api_bytes(method: str, path: str, *, timeout: float = 60.0) -> bytes | None:
    """Variant that returns raw bytes (for file downloads like Excel)."""
    url = f"{API_BASE}{path}"
    try:
        resp = httpx.request(method, url, timeout=timeout, headers=auth_headers())
        if resp.status_code == 401:
            logout()
            return None
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        st.warning(f"Не вдалося завантажити файл: {exc}")
        return None
