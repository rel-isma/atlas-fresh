# Atlas Fresh — Daily Apple Export Planner

**Stage AI Product Engineer — test technique week-end**

A decision-support workspace for Atlas Fresh's daily Production–Commercial meeting: replaces manual spreadsheet reconciliation with a server-computed, deterministic export plan and a small AI layer that explains — never makes — that plan.

## The problem

20 farms deliver apples across four quality segments (A best, D lowest); 10 clients have contracted volumes, quality rules and prices; the export station processes at most 500 t/day. Actual output rarely matches plan. The app decides, daily, which farm-segment tonnes serve which client, who ends up short and why, and how much unexported fruit falls back to the low-value local market.

## Key business rules (deterministic, not an optimizer, not an LLM)

- Supply = actual A/B/C/D tonnes only; planned figures are comparison-only.
- Clients processed by price descending, tie-broken by client ID.
- `EXACT` accepts only the requested segment; `MINIMUM` accepts that segment or better (A > B > C > D).
- Compatible supply ordered by smallest quality upgrade, then farm ID.
- Allocation in 5 t steps until demand, supply, or the 500 t station capacity is exhausted.
- Unexported tonnes go local at 10% of the segment's reference price.
- Client status `COMPLETE`/`PARTIAL`/`UNSERVED`, with reason `STATION_CAPACITY_REACHED` or `INSUFFICIENT_COMPATIBLE_SEGMENT` when not complete.

Same input always produces the same output — no hidden state.

## Architecture

`Excel (read-only) -> loader -> validation -> deterministic engine -> FastAPI (camelCase JSON) -> React frontend (one fetch) -> Assistant (explains, never computes)`

Backend: FastAPI + Pydantic, with the entire engine (`app/core/`) as pure Python — no FastAPI/DB/AI imports there, so it's testable in isolation and can't silently duplicate business logic. Frontend: Vite + React + TypeScript + Tailwind v4, one API call populates the whole app.

## Frontend

- **Overview** — KPIs, expected-vs-actual chart, dynamic narrative, at-risk/local-residual previews.
- **Production** — one row per farm, expandable to per-segment variance and which clients each segment served; filterable by segment/deficit.
- **Commercial** — one row per client (price-sorted), expandable to its full farm-level allocation, status and reason in plain language; filterable by status.
- **Local Residual** — local-market tonnes and value by farm/segment.

Allocation traceability (farm, segment, client, tonnes, quality upgrade, revenue) lives inside Commercial's per-client drill-down rather than a separate screen.

## AI approach and guardrails

Read-only explanation layer over the computed plan. Answers from a structured context built from the real result (not the raw workbook); every cited ID is checked against the plan and stripped/rejected if unresolvable. Without `ANTHROPIC_API_KEY` it falls back to a fully deterministic, template-based answer — same grounding, no model call — the default in this repo.

## Testing — 28 backend tests, all passing

- `test_engine.py` — ordering, compatibility, capacity limit, local residual conservation, baseline reproduction, farm-level variance.
- `test_assistant_core.py` — grounded citations, ID-guard rejection, honest handling of unsupported questions.
- `test_api.py` — HTTP boundary: healthy response, 422 on invalid data, assistant request validation.

## Prerequisites

Python 3.11+, Node 18+.

## Run it (clean-start path)

```bash
git clone https://github.com/rel-isma/atlas-fresh.git
cd atlas-fresh

# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v                       # 28 passed
uvicorn app.main:app --reload   # http://localhost:8000

# frontend (new terminal)
cd frontend
cp .env.example .env
npm install && npm run dev      # http://localhost:5173
```
No API key required for either to run fully.

## Assumptions & limitations

- One daily snapshot from the supplied seed workbook; no upload UI.
- `local_market_ratio` is trusted source config, not range-validated.
- Free-text assistant relevance is a keyword filter, not semantic NLP.
- No persistence (recomputes from the seed workbook each load) and no authentication — both intentionally out of scope.

## Deployment (optional)

Both apps are deployable to Vercel with zero backend config beyond two
environment variables: `ALLOWED_ORIGINS` on the backend (the deployed
frontend's URL) and `VITE_API_BASE_URL` on the frontend (the deployed
backend's URL). No database, no Docker — Vercel's zero-config Python
runtime detects `app/main.py` directly.

**Live demo:** https://atlas-fresh-frontend.vercel.app/

## Next three production steps

1. Persist daily planning snapshots to enable historical trend and performance comparison.
2. Enable a real LLM provider behind a feature flag, with fallback to the deterministic assistant.
3. Add role-aware views so Production and Commercial users see the most relevant default screens.

## AI tools used

Built with Claude as primary engineering collaborator (architecture, backend, tests) and problem-solving support from ChatGPT alongside Claude during development. Lovable was used for frontend visual design, with Antigravity used for frontend implementation against a hand-specified design and API contract. Business logic was specified explicitly and verified against the workbook's baseline, not generated freely.