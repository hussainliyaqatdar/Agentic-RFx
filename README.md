# Agentic RFx

An AI-native RFx flow: a buyer drafts an RFx by talking to a co-pilot, it goes out to vendors,
vendor replies arrive in whatever format they show up in (spreadsheet, PDF, Word doc, photo of a
rate card, plain email text), an extraction/normalization agent lands everything in one
side-by-side comparison, and an analyst-chat agent answers natural-language questions grounded in
that comparison through to an award decision.

Fictional buyer: **YoloMart**. Category: corrugated packaging. Five vendors, thirty line items, a questionnaire.

## Stack

- **Backend**: FastAPI + SQLModel (SQLite), Python managed via [uv](https://docs.astral.sh/uv/).
- **LLM**: Google Gemini (`gemini-3.8-flash`) via the `google-genai` SDK.
- **Frontend**: React + Vite + TypeScript + Tailwind CSS v4 + React Router.

## Setup

**Backend**

```bash
cd backend
cp .env.example .env      # then paste your GEMINI_API_KEY into .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`, and once the key is in `.env`,
`curl http://127.0.0.1:8000/health/llm` round-trips a real Gemini call.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — dev requests to `/api/*` are proxied to the backend on `:8000`, so
no CORS config or `VITE_API_URL` is needed locally.

## Layout

```
backend/app/
  models/       SQLModel schema - see below
  routers/      FastAPI route modules
  services/
    llm/        Gemini client wrapper, retry policy, cost tracking
    extraction/ Module 3 - document loader, worker agent, evaluator agent, merge
  evals/        offline harness - runs extraction against the 5 fabricated vendors,
                scores it against data/seed/vendors/ground_truth.json
  db.py         engine + session + init_db()
  main.py       app entrypoint
frontend/src/
  pages/        one page per module (list, co-pilot, comparison, chat)
  lib/api.ts    fetch helper
data/seed/      fabricated dataset - see its README
```

## Data model

Defined in `backend/app/models/`, one table per file grouped by domain:

- `rfx.py` — `Rfx`, `RfxLineItem` (canonical SKUs the buyer wants quoted), `RfxQuestion`
  (questionnaire), `RfxVendor` (which vendors an RFx was sent to, and their response status).
- `vendor.py` — `Vendor`, and `HistoricalPrice` (last period's pricing per SKU, for resolving
  "rest same as last year" style replies).
- `documents.py` — `VendorResponseDocument`, the raw file/email text exactly as a vendor sent it.
  Extraction always reads from here, never from a pre-cleaned copy.
- `extraction.py` — `ExtractedLineQuote` (one vendor's quoted price for one matched line item,
  original + normalized values, `match_confidence` and `extraction_confidence` tracked separately,
  `source_citation` pointing back into the original document) and `ExtractedAnswer` (questionnaire
  answers, same confidence/citation shape).
- `award.py` — `AwardLineItem`, one row per line item so an RFx can be split-awarded across
  vendors; a single-vendor award is just the case where every row points at the same vendor.
- `chat.py` — `ChatSession` / `ChatMessage`, shared by both the RFx-drafting co-pilot and the
  analyst chat (`session_type` distinguishes them), with `tool_calls` kept per message so answers
  stay traceable back to the query that produced them.

## Module 3: extraction & entity resolution

The crux module is implemented and running against real Gemini calls, not stubbed:

- **Worker agent**: one Gemini call per vendor, given that vendor's raw documents (xlsx/pdf/docx/
  image/email, however many) plus the canonical line items, questionnaire, and buyer terms. Matches
  by spec rather than assuming vendor codes line up, normalizes units/currency, and cites its
  source for every value.
- **Evaluator agent**: a second, independent Gemini call - adversarial framing, same documents,
  reviews the worker's claims without seeing its reasoning. Re-derives values rather than checking
  plausibility, and separately checks *completeness*: whether the documents support pricing any
  canonical item the worker didn't claim at all (e.g. a vendor's blanket rate that was never
  expanded across the items it covers).
- **Merge**: deterministic combination of worker + evaluator output into final records, with
  `needs_review` and the evaluator's reasoning attached - never silently dropped.
- **Eval harness** (`backend/app/evals/`): runs the pipeline against all 5 fabricated vendors and
  scores the result against the authored ground truth - SKU-match accuracy, price accuracy,
  coverage precision, questionnaire accuracy. Run with:
  ```bash
  cd backend
  uv run python -m app.evals.run_evals
  ```
  Every Gemini call is cost-tracked from the API's own token usage and hard-capped by
  `cost_tracker.SESSION_BUDGET_USD` (default $1) - it refuses to make another call once the session
  spend reaches that cap.

Modules 1, 2, 4, and 5 (co-pilot, review workflow, comparison UX, analyst chat) are not wired up
yet - only their placeholder pages and schema exist so far.

**Deliberately out of scope for v0**: real email send/receive (fully simulated — vendor responses
are ingested as manually-attached files, not a live inbox), auth/multi-tenant, live FX rates, and
anything post-award (contracts, e-sign, PO generation).
