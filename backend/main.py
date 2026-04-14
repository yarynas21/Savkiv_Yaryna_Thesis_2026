"""
Dyz-Art MAS — FastAPI Backend
==============================
Exposes the LangGraph multi-agent workflow as a REST API.

Endpoints:
  POST /api/sessions                        → create session
  POST /api/sessions/{thread_id}/messages   → send user message
  POST /api/sessions/{thread_id}/review     → submit expert feedback
  GET  /api/sessions/{thread_id}/excel      → download Excel work order

Run:
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is the Python root so internal imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv(Path(__file__).parent.parent / ".env")

from api.routes import router
from auth.routes import router as auth_router
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Compile the LangGraph workflow once on startup and store it in app.state."""
    logger.info("Starting up — compiling LangGraph workflow...")
    from graph.workflow import compile_workflow

    app.state.workflow = compile_workflow()
    logger.info("Workflow ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Dyz-Art MAS API",
    description="Multi-Agent System for Production Workflow Generation in the Printing Industry",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
