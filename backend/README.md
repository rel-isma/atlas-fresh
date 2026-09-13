# Atlas Fresh — Backend

FastAPI backend for the Atlas Fresh Daily Export Planner. Implements a
pure, deterministic planning engine over the authoritative Atlas Fresh
workbook, exposed through two read-only HTTP endpoints, plus a small
grounded (non-AI-dependent) assistant.

## Architecture

```
backend/
├── app/
│   ├── main.py              FastAPI app: CORS + router mounting only
│   ├── api/
│   │   ├── plan.py          GET /api/plan  (thin route)
│   │   ├── assistant.py     POST /api/assistant  (thin route)
│   │   └── schemas.py       Pydantic response models (camelCase JSON)
│   └── core/                 PURE PYTHON. No FastAPI/Pydantic imports.
│       ├── models.py         Domain dataclasses (source + calculated)
│       ├── loader.py         Mechanical .xlsx extraction only
│       ├── validation.py     Business rules -> ValidationIssue list
│       ├── engine.py         allocate() — the deterministic policy
│       ├── narrative.py      Dynamic narrative text generation
│       └── assistant/
│           ├── context.py    Builds minimal context from PlanResult
│           ├── guard.py      Rejects/strips unknown cited IDs
│           └── provider.py   FallbackProvider (deterministic, no AI)
├── data/
│   └── Atlas_Fresh_Production_Commercial_Data.xlsx   (read-only seed)
├── tests/
│   ├── test_engine.py         6 approved engine tests
│   ├── test_assistant_core.py  Assistant grounding tests (pure)
│   └── test_api.py             API boundary tests (FastAPI TestClient)
└── requirements.txt
```

**Dependency direction is one-way:** `app/api` depends on `app/core`;
`app/core` never imports FastAPI, Pydantic, HTTP, or database
libraries. The engine (`core/engine.py`) is fully independent of the
web framework and can be imported and tested with zero infrastructure.

## Requirements

- Python 3.11+
- pip

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the tests

```bash
pytest -v
```

Expected: all tests in `test_engine.py`, `test_assistant_core.py`, and
`test_api.py` pass. See "Known limitation" below regarding the
environment this backend was originally built in.

## Run the server

```bash
uvicorn app.main:app --reload
```
Server starts at `http://localhost:8000`. CORS is pre-configured for a
Vite dev server at `http://localhost:5173`.

## API

### `GET /api/plan`

Loads the workbook at `backend/data/Atlas_Fresh_Production_Commercial_Data.xlsx`
(read-only — never modified), validates it, and if valid, runs the
deterministic engine and returns the complete plan.

- **200** — `{ dataHealth: "healthy", kpis, narrative, segmentVariances,
  farmSegmentBalances, clientResults, allocations, localResidual }`
- **422** — `{ dataHealth: "invalid", validationErrors: [{ sheet, id, field, message }] }`
- **500** — workbook missing, unreadable, or an unexpected server error
  (never returned as if it were a successful or "invalid data" result)

Recomputes from disk on every call — no caching, no persistence. This
is deliberate: an evaluator swapping the workbook file and re-calling
the endpoint gets a freshly computed result with zero extra code.

### `POST /api/assistant`

Body: `{ "question": "at_risk_clients" | "farm_gaps" | "local_residual" }`
or `{ "freeText": "..." }`.

- **200** `{ available: true, answer, citedIds, source: "fallback" }`
- **200** `{ available: false, reason, fallbackAnswer? }` — for an
  unsupported question, a missing/invalid workbook, or a provider
  failure. Never returns a fabricated answer.

Only `FallbackProvider` exists in this phase — a deterministic,
dependency-free answer generator built directly from the same
`PlanResult` the planning endpoint returns. `app/core/assistant/provider.py`
defines the `AssistantProvider` interface so a real LLM-backed
provider can be added later without touching `context.py`, `guard.py`,
or the routes. Every cited farm/client ID is checked by
`guard.ensure_grounded()` against the current `PlanResult` before
being returned — unknown IDs are stripped, and an answer that cited
only unknown IDs is rejected outright.

## Deterministic engine boundary

`app/core/engine.py` exposes exactly one public function, `allocate()`,
implementing the documented policy: actual production only (planned
values are comparison-only), clients processed price-descending with
`client_id` tie-break, EXACT/MINIMUM segment compatibility, smallest-
quality-upgrade-then-`farm_id` candidate ordering, 5-tonne allocation
steps, a single global station-capacity constraint, and all remaining
actual supply falling back to the local market. See `test_engine.py`
for the six tests covering ordering, compatibility, the capacity hard
limit, local-residual conservation, and full baseline reproduction.

## Validation behavior

`app/core/validation.py` checks IDs, modes, segments, the segment
price table, mix-fraction sums, quantity granularity (5t multiples),
and non-negativity — collecting every issue in one pass rather than
failing on the first. Invalid input is never silently repaired; the
engine never runs on invalid input. `local_market_ratio` is
intentionally **not** range-validated — it is trusted source
configuration, used exactly as supplied.

## Known limitation (this build environment)

This backend was implemented in a sandboxed environment with no
network access, so `fastapi`, `pydantic`, `uvicorn`, and `httpx` could
not be installed there, and consequently `app/main.py`, `app/api/*.py`,
and `tests/test_api.py` could not be executed or live-verified in that
environment. They were written carefully against the documented
Pydantic v2 / FastAPI API and against the already-verified engine
output, but you should run `pytest -v` and `uvicorn app.main:app --reload`
yourself as the first verification step after cloning. Everything in
`app/core/` (including the assistant's context/guard/provider logic)
**was** executed and verified in that environment, since it has no
external dependencies beyond `openpyxl` and the Python standard
library.
