"""FastAPI application entry point.

Deliberately small: creates the app, configures CORS, and mounts the
two routers. No business logic lives here — see app/core for the
deterministic engine and app/api for the thin route handlers.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

# Load backend/.env (if present) before anything reads os.environ —
# in particular provider.get_default_provider(), which checks for
# ANTHROPIC_API_KEY. Safe to call even if no .env file exists; it's a
# no-op in that case. Real secrets live only in .env (gitignored),
# never in source.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import assistant, plan

app = FastAPI(title="Atlas Fresh — Daily Export Planner API")

# Comma-separated list of allowed frontend origins. Defaults to the
# local Vite dev server. In production (e.g. Vercel), set
# ALLOWED_ORIGINS to the deployed frontend's real URL via the
# platform's environment variable settings — never hardcode a
# deployed URL into source.
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(plan.router)
app.include_router(assistant.router)


@app.get("/health")
def health():
    """Basic liveness check — not part of the assessment's required
    API surface, but a near-zero-cost way to confirm the server is up
    before hitting /api/plan."""
    return {"status": "ok"}
