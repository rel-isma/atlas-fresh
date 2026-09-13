"""FastAPI application entry point.

Deliberately small: creates the app, configures CORS for the local
Vite dev server, and mounts the two routers. No business logic lives
here — see app/core for the deterministic engine and app/api for the
thin route handlers.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import assistant, plan

app = FastAPI(title="Atlas Fresh — Daily Export Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
