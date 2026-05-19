# Sagard AI Portfolio Intelligence & Risk Escalation Copilot

A lightweight, end-to-end prototype of an AI system for an Investments-team member at Sagard. It ingests internal portfolio-company documents, fuses them with external market signals, runs a RAG-backed risk analysis, and routes a Slack-style alert to the deal team — with the **final decision left to a human analyst.**

This is a take-home submission for the Sagard AI Builder / Forward Deployed Engineer role.

---

## 1. What the system does

For any portfolio company the system will:

1. **Ingest internal documents** — investment memo, quarterly update, financial summary, board notes.
2. **Chunk + embed** the documents into an in-memory vector index.
3. **Pull external signals** — competitor funding, hiring velocity, customer reviews, market news (mocked, swap-in ready).
4. **Run a structured RAG analysis** — retrieves evidence for seven canonical diligence questions and feeds it to an LLM (Claude or OpenAI). If no API key is configured, a deterministic rule-based fallback produces the same JSON shape so the demo always runs.
5. **Produce a structured report** — executive summary, positive signals, risk signals, follow-up diligence questions, **Low / Medium / High** risk score, and a *suggested* next action (never a buy/sell).
6. **Send a Slack-style alert** to the deal team (real Slack webhook if `SLACK_WEBHOOK_URL` is set, otherwise simulated and logged to the DB).
7. **Wait for a human decision** — *Escalate to IC*, *Request More Diligence*, or *Mark as Reviewed*. The audit trail is stored in `human_reviews`.

## 2. Why this helps Sagard

Sagard monitors a multi-strategy book across VC, PE, private credit, real estate, and wealth. A single analyst can easily be responsible for dozens of companies. The painful part of the job is **noticing**, not deciding: spotting that burn-rate, churn, and a CFO departure showed up in the *same* quarter and connecting that to a competitor's new funding round.

This copilot does the noticing — at machine speed, across documents and external signals — and hands a structured, evidence-backed brief to the analyst, who keeps the judgment call. The analyst's decision is logged for compliance and IC audit purposes.

## 3. Tools / systems connected (≥ 2 integrations)

| Layer            | Prototype                                  | Production swap                                   |
|------------------|--------------------------------------------|---------------------------------------------------|
| Document store   | SQLite + filesystem                        | SharePoint / Box / S3                             |
| Vector / RAG     | In-memory hashed embeddings + cosine search| OpenAI / Voyage embeddings + Chroma / pgvector    |
| LLM              | Anthropic Claude or OpenAI (auto-detected) | Same, via API gateway with audit logging          |
| External signals | Mocked competitor / hiring / reviews / news| PitchBook, LinkedIn Talent Insights, G2, news APIs|
| Notification     | Slack webhook (or simulated)               | Slack + email + Teams                             |
| Orchestration    | `n8n-workflow.json` (provided)             | Hosted n8n / Temporal / Airflow                   |
| Persistence      | SQLite                                     | PostgreSQL                                        |

**Two real integration points are exercised end-to-end in the prototype: (a) the LLM (Anthropic or OpenAI) and (b) the Slack webhook.** Both gracefully degrade to local simulation so the demo never blocks on a missing key.

## 4. Human decision point

The AI **never** makes the final investment decision. After analysis, the UI presents three buttons:

- **Escalate to Investment Committee**
- **Request More Diligence**
- **Mark as Reviewed**

The selected decision, the reviewer, and the timestamp are persisted to `human_reviews` and visible on the company page's *Decision History*. The n8n workflow's `Wait for Human Review` node mirrors this — the workflow only resumes once the analyst has chosen.

## 5. How to run locally

**Prereqs:** Python 3.10+, internet access for first-run React CDN load.

```bash
# from the project root
pip install -r requirements.txt

# (optional) configure real integrations
export ANTHROPIC_API_KEY=sk-ant-...        # or OPENAI_API_KEY=sk-...
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# start the server (auto-seeds the DB on first run)
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** — that's it. No npm install, no separate frontend build; the React SPA is served from `frontend/index.html` and loads React from CDN.

If you ever want to wipe the database and re-seed:

```bash
rm sagard.db
python -m backend.seed
```

## 6. Demo script (2–3 minutes)

1. **(0:00) Land on the Dashboard.** Three portfolio companies are loaded: FinPay Analytics (FinTech SaaS), GreenLeaf Logistics (climate / supply chain), NovaBio Diagnostics (HealthTech). Each card shows sector, stage, invested amount, ownership, and (after analysis) a risk badge.
2. **(0:20) Open FinPay Analytics.** Scroll to show four internal documents (memo, quarterly, financial summary, board notes) and four external signals (competitor funding, hiring slowdown, customer reviews, market demand).
3. **(0:40) Click "Run AI Analysis".** The backend builds the RAG index over the four documents, retrieves evidence for seven canonical diligence questions, then calls the LLM (or deterministic fallback). About 1–2 seconds later the report renders:
    - Risk: **High**
    - Positive: revenue grew 80% YoY, market demand strong
    - Risks: burn +45%, churn 4%→11%, sales cycle 45→82 days, CFO departure, implementation delays
    - Five precise follow-up questions
    - Suggested next step (framed as a suggestion only)
4. **(1:20) Expand "RAG evidence used for this analysis"** to show the actual document excerpts retrieved for each diligence question — this is the auditable trail.
5. **(1:40) Open the Alerts tab.** A Slack-style notification has already been dispatched to `#investments-portfolio-monitoring` (or simulated, with the message logged).
6. **(2:00) Back to FinPay → click "Escalate to IC".** The decision is recorded under *Decision History* with the reviewer name and timestamp.
7. **(2:30) Open the Workflow tab.** Show the orchestration graph (Upload → Extract → Retrieve → Analyze → Alert → Human Review). Cross-reference with `n8n-workflow.json`.
8. **(Optional, 0:20) Open NovaBio Diagnostics, run analysis** — comes back **Low** risk, showing the system isn't just flagging everything.

## 7. What would break first at 10× scale

The single biggest fragility is **retrieval quality at scale**. The current in-memory hashed-token embedding is deterministic and free, but it has roughly the precision of BM25 — fine for ~12 documents per company, but win-rate drops fast at 100+ documents per company × 200+ companies. The first production upgrade is real embeddings (Voyage / OpenAI) + Chroma or pgvector with per-company namespacing.

Second-most-fragile is **external signal ingestion**. The mocked signals are fine for a demo, but real PitchBook / LinkedIn / G2 ingestion needs rate-limiting, deduplication, sentiment scoring at the source, and freshness windows.

Third is the **LLM call itself** — at 10× volume the deterministic fallback is no longer a fallback, it's a denial-of-service issue. Production needs queued requests, per-tenant quotas, structured output validation (json-schema enforcement), and cost monitoring.

Lastly, **access control**. The prototype assumes a single trusted analyst. Production needs SSO, deal-team-scoped access on every endpoint, row-level RLS for cross-fund isolation, and full audit logging for SOX / fiduciary compliance.

## 8. File layout

```
sagard/
├── README.md                       ← this file
├── submission-explanation.md       ← 250-word writeup
├── n8n-workflow.json               ← orchestration graph
├── requirements.txt                ← Python deps
├── backend/                        ← FastAPI app
│   ├── main.py                     ← API endpoints + static serving
│   ├── database.py                 ← SQLAlchemy engine
│   ├── models.py                   ← ORM models (6 tables)
│   ├── schemas.py                  ← Pydantic response schemas
│   ├── rag_service.py              ← chunking + retrieval
│   ├── ai_service.py               ← LLM call + deterministic fallback
│   ├── notification_service.py     ← Slack webhook / simulator
│   └── seed.py                     ← loads three sample companies
├── frontend/
│   └── index.html                  ← single-file React SPA (CDN React + Babel)
└── data/                           ← sample portfolio documents
    ├── finpay_*.md
    ├── greenleaf_*.md
    └── novabio_*.md
```

## 9. API surface

| Method | Path                              | Purpose                                            |
|-------:|-----------------------------------|----------------------------------------------------|
| GET    | `/api/companies`                  | List companies + latest risk score + open-alert flag |
| GET    | `/api/companies/{id}`             | Full detail: docs, signals, latest report, reviews |
| POST   | `/api/analyze/{company_id}`       | Run RAG + AI analysis, persist, dispatch alert     |
| POST   | `/api/review/{company_id}`        | Record human decision                              |
| GET    | `/api/alerts`                     | All Slack-style notifications sent                 |
| GET    | `/api/workflow`                   | Static workflow steps (mirrors n8n JSON)           |

## 10. Database tables

`companies`, `documents`, `external_signals`, `ai_reports`, `human_reviews`, `alerts` — six tables, all defined in `backend/models.py`. Storage is SQLite for zero-config; the schema is portable to PostgreSQL by swapping the SQLAlchemy URL.

---

**Author:** Hugh — submission for Sagard Engineering AI Builder / FDE.
